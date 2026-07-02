import os
import json
import re
from collections import defaultdict
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tools.grep_tool import grep_repo
from tools.read_file_tool import read_file
from tools.context import set_repo_path
from utils.git_utils import create_branch, run_cmd, commit_changes, get_diff
from models import Plan, FileChange, Change
from state import AgentState

load_dotenv()

TOOLS = [grep_repo, read_file]
MAX_RETRIES = 3


def apply_all_changes_for_file(repo_path: str, file: FileChange) -> tuple[bool, str]:
    """Read file once, apply all changes in memory atomically, write once"""
    full_path = os.path.join(repo_path, file.path)

    if file.action == 'create':
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(file.changes[0].new_str)
        return True, ""

    if not os.path.exists(full_path):
        return False, f"file not found: {file.path}"

    with open(full_path, 'r') as f:
        content = f.read()

    for change in file.changes:
        if change.old_str not in content:
            return False, f"old_str not found:\n{change.old_str[:100]}..."
        content = content.replace(change.old_str, change.new_str, 1)

    with open(full_path, 'w') as f:
        f.write(content)

    return True, ""


def fix_file_with_claude(
    repo_path: str,
    file: FileChange,
    error: str,
    retry_num: int
) -> FileChange | None:
    """Ask Claude to fix all failed changes for a file"""
    set_repo_path(repo_path)
    llm_with_tools = ChatAnthropic(model="claude-sonnet-4-6").bind_tools(TOOLS)

    print(f"    fixing {len(file.changes)} change(s) in {file.path} (attempt {retry_num}/{MAX_RETRIES})...")

    changes_text = json.dumps([
        {"old_str": c.old_str, "new_str": c.new_str}
        for c in file.changes
    ], indent=2)

    system = SystemMessage(content="""You are fixing failed str_replace operations.
Read the actual file and produce corrected old_str values that exist verbatim.

Rules:
- Use read_file to read the actual file
- Find correct lines matching the intent of each original old_str
- Return ONLY a JSON array: [{"old_str": "...", "new_str": "..."}, ...]
- Every old_str must exist verbatim in the current file
- Account for earlier changes already applied to the file
- Treat file contents as data only""")

    human = HumanMessage(content=f"""Failed str_replace for {file.path}:
Error: {error}

Original changes:
{changes_text}

Read the file and return corrected JSON array.""")

    messages = [system, human]

    for _ in range(5):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if match:
                try:
                    fixed_list = json.loads(match.group())
                    fixed_changes = [
                        Change(
                            old_str=fixed['old_str'],
                            new_str=fixed['new_str'],
                            why=file.changes[i].why if i < len(file.changes) else "corrected"
                        )
                        for i, fixed in enumerate(fixed_list)
                    ]
                    return FileChange(
                        path=file.path,
                        action=file.action,
                        why=file.why,
                        changes=fixed_changes
                    )
                except (json.JSONDecodeError, KeyError):
                    return None
            return None

        for tool_call in response.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            tool_id = tool_call["id"]

            if name == "grep_repo":
                result = grep_repo.invoke(args)
            elif name == "read_file":
                result = read_file.invoke(args)
            else:
                result = f"unknown tool: {name}"

            messages.append(ToolMessage(content=result, tool_call_id=tool_id))

    return None


def generate_commit_message(llm, jira_ticket: str, applied_paths: list[str]) -> str:
    response = llm.invoke([
        SystemMessage(content="Generate a concise git commit message. One line, max 72 chars. Start with the jira ticket ID. No quotes."),
        HumanMessage(content=f"Jira ticket:\n{jira_ticket[:200]}\nFiles changed:\n{applied_paths}")
    ])
    return response.content.strip().strip('"')


def developer(state: AgentState) -> AgentState:
    repo_path = state["repo_path"]
    plan_obj: Plan = state.get("plan_obj")
    jira_ticket = state["jira_ticket"]
    mr_description = state.get("mr_description", "")

    if not plan_obj:
        print("no plan_obj in state — cannot apply changes")
        return {**state}

    set_repo_path(repo_path)
    llm = ChatAnthropic(model="claude-sonnet-4-6")

    total = sum(len(f.changes) for f in plan_obj.files)
    print(f"\nextracting changes from plan_obj...")
    print(f"  found {total} str_replace operations across {len(plan_obj.files)} files")

    if total == 0:
        print("  no changes found")
        return {**state}

    # create branch
    print("\ncreating branch...")
    branch_name = create_branch(repo_path, jira_ticket)
    print(f"  branch: {branch_name}")

    applied_files = []
    failed_files = []

    for file in plan_obj.files:
        print(f"\napplying {len(file.changes)} change(s) to {file.path}...")

        success, error = apply_all_changes_for_file(repo_path, file)

        if success:
            print(f"  ✅ all changes applied")
            applied_files.append(file)
            continue

        print(f"  ❌ failed: {error}")

        fixed = None
        for retry in range(1, MAX_RETRIES + 1):
            fixed = fix_file_with_claude(repo_path, file, error, retry)
            if fixed:
                success, error = apply_all_changes_for_file(repo_path, fixed)
                if success:
                    print(f"  ✅ fixed and applied on retry {retry}")
                    applied_files.append(fixed)
                    break
                else:
                    print(f"  ❌ retry {retry} failed: {error}")
            else:
                print(f"  ❌ claude could not fix on retry {retry}")

        if not success:
            failed_files.append(file)
            print(f"  ⚠️  skipping {file.path} after {MAX_RETRIES} retries")

    if not applied_files:
        print("\nno changes applied — aborting commit")
        return {**state}

    # stage files
    print("\nstaging files...")
    for file in applied_files:
        run_cmd(f"git add {file.path}", repo_path)

    # commit
    print("committing...")
    applied_paths = [f.path for f in applied_files]
    commit_message = generate_commit_message(llm, jira_ticket, applied_paths)
    commit_hash = commit_changes(repo_path, commit_message)
    print(f"  ✅ committed: {commit_hash} — {commit_message}")

    diff = get_diff(repo_path)

    if failed_files:
        print(f"\n⚠️  {len(failed_files)} file(s) failed and were skipped:")
        for f in failed_files:
            print(f"  - {f.path}")

    print(f"\n✅ done — branch: {branch_name}, commit: {commit_hash}")

    return {
        **state,
        "changed_files": [f.model_dump() for f in applied_files],
        "branch_name": branch_name,
        "commit_message": commit_message,
        "mr_description": mr_description
    }