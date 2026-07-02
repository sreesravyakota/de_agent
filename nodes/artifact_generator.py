import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from utils.ast_parser import (
    build_ast_map,
    build_file_table_map,
    ast_map_to_markdown,
    file_table_map_to_markdown
)
from tools.grep_tool import grep_repo
from tools.read_file_tool import read_file
from tools.context import set_repo_path
from state import AgentState

load_dotenv()

ARTIFACTS_DIR = "artifacts"
TOOLS = [grep_repo, read_file]


def generate_tree_md(repo_path: str) -> str:
    lines = ["# Repo Tree\n"]
    repo_name = os.path.basename(os.path.abspath(repo_path))
    lines.append(f"{repo_name}/")
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in [
            '__pycache__', '.git', 'venv', 'node_modules', 'artifacts'
        ]]
        level = os.path.relpath(root, repo_path).count(os.sep)
        if level == 0:
            indent = "  "
        else:
            indent = "  " * (level + 1)
        
        for d in sorted(dirs):
            lines.append(f"{indent}{d}/")
        for f in sorted(files):
            if not f.endswith(('.png', '.PNG', '.docx', '.log', '.pyc')):
                lines.append(f"{indent}{f}")
    
    return "\n".join(lines)


def generate_claude_md(repo_path: str, tree_md: str, ast_map_md: str) -> str:
    llm = ChatAnthropic(model="claude-sonnet-4-6").bind_tools(TOOLS)

    system = SystemMessage(content="""You are an expert data engineering assistant analyzing a repository.
Your job is to explore the repo using grep_repo and read_file tools then produce a CLAUDE.md file.

RULES:
- Never use '.' as a grep pattern — it matches everything and wastes tool calls
- Use specific patterns: class names, function names, table names, import statements, SQL keywords
- Read the DAG file first — it is the entry point and references everything else
- Follow imports to understand the full dependency chain
- Read SQL query files to understand table schemas and naming conventions
- Max 15 tool calls — be deliberate, each call should reveal something new

CLAUDE.md MUST contain:
1. What this repo does (2-3 sentences max)
2. Folder structure — what lives where and why
3. Step by step: how to add a new staging table (exact files to touch, in order)
4. Step by step: how to add a new warehouse table (exact files to touch, in order)
5. Step by step: how to add a new DAG task (exact files to touch, in order)
6. Key conventions (naming patterns, SQL style, operator patterns, schema names)
7. Entry point files vs helper files
8. Table inventory: all known staging + warehouse + analytics tables

Be dense and specific — this is context for an AI agent not a human.
When done exploring respond with CLAUDE.md content directly — no preamble, no markdown code fences.""")

    human = HumanMessage(content=f"""Explore this data engineering repo and generate CLAUDE.md.

--- REPO TREE ---
{tree_md}

--- AST MAP ---
{ast_map_md}

Use grep_repo and read_file to explore further then write the CLAUDE.md.""")

    messages = [system, human]
    tool_calls = 0
    max_tool_calls = 15

    while tool_calls < max_tool_calls:
        response = llm.invoke(messages)
        messages.append(response)

        # no tool calls — claude is done
        if not response.tool_calls:
            return response.content

        # process tool calls
        for tool_call in response.tool_calls:
            tool_calls += 1
            name = tool_call["name"]
            args = tool_call["args"]
            tool_id = tool_call["id"]

            print(f"  tool call {tool_calls}/{max_tool_calls}: {name}({args})")

            if name == "grep_repo":
                result = grep_repo.invoke(args)
            elif name == "read_file":
                result = read_file.invoke(args)
            else:
                result = f"unknown tool: {name}"

            messages.append(ToolMessage(
                content=result,
                tool_call_id=tool_id
            ))

    # hit limit — ask claude to wrap up
    print(f"  hit {max_tool_calls} tool call limit, wrapping up...")
    messages.append(HumanMessage(
        content="You have reached the tool call limit. Write the CLAUDE.md now based on what you explored."
    ))

    final = llm.invoke(messages)
    return final.content


def artifact_generator(state: AgentState) -> AgentState:
    repo_path = state["repo_path"]

    # set repo_path globally so tools can access it
    set_repo_path(repo_path)

    artifacts_path = os.path.join(os.path.dirname(__file__), '..', ARTIFACTS_DIR)
    os.makedirs(artifacts_path, exist_ok=True)

    # --- tree.md ---
    tree_path = os.path.join(artifacts_path, "tree.md")
    if os.path.exists(tree_path):
        print("✓ tree.md exists, skipping")
        with open(tree_path) as f:
            tree_md = f.read()
    else:
        print("generating tree.md...")
        tree_md = generate_tree_md(repo_path)
        with open(tree_path, 'w') as f:
            f.write(tree_md)
        print("✓ tree.md generated")

    # --- ast_map.md ---
    ast_path = os.path.join(artifacts_path, "ast_map.md")
    if os.path.exists(ast_path):
        print("✓ ast_map.md exists, skipping")
        with open(ast_path) as f:
            ast_map_md = f.read()
    else:
        print("generating ast_map.md...")
        ast_map = build_ast_map(repo_path)
        ast_map_md = ast_map_to_markdown(ast_map)
        with open(ast_path, 'w') as f:
            f.write(ast_map_md)
        print("✓ ast_map.md generated")

    # --- file_table_map.md ---
    ftm_path = os.path.join(artifacts_path, "file_table_map.md")
    if os.path.exists(ftm_path):
        print("✓ file_table_map.md exists, skipping")
        with open(ftm_path) as f:
            file_table_map_md = f.read()
    else:
        print("generating file_table_map.md...")
        ast_map = build_ast_map(repo_path)
        file_table_map = build_file_table_map(ast_map)
        file_table_map_md = file_table_map_to_markdown(file_table_map)
        with open(ftm_path, 'w') as f:
            f.write(file_table_map_md)
        print("✓ file_table_map.md generated")

    # --- CLAUDE.md ---
    claude_path = os.path.join(artifacts_path, "CLAUDE.md")
    if os.path.exists(claude_path):
        print("✓ CLAUDE.md exists, skipping")
        with open(claude_path) as f:
            claude_md = f.read()
    else:
        print("generating CLAUDE.md (exploring repo with tools)...")
        claude_md = generate_claude_md(repo_path, tree_md, ast_map_md)
        with open(claude_path, 'w') as f:
            f.write(claude_md)
        print("✓ CLAUDE.md generated")

    return {
        **state,
        "tree_md": tree_md,
        "ast_map_md": ast_map_md,
        "file_table_map_md": file_table_map_md,
        "claude_md": claude_md
    }