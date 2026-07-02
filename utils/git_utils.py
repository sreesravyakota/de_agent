import os
import subprocess
from datetime import datetime
import re


def run_cmd(cmd: str, cwd: str) -> tuple[int, str, str]:
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def create_branch(repo_path: str, jira_ticket: str) -> str:
    first_line = next((l.strip() for l in jira_ticket.split('\n') if l.strip()), "agent-branch")
    ticket_slug = first_line[:40].lower()
    ticket_slug = ''.join(c if c.isalnum() else '-' for c in ticket_slug)
    ticket_slug = re.sub(r'-+', '-', ticket_slug)  # collapse multiple dashes
    ticket_slug = ticket_slug.strip('-')
    branch_name = f"agent/{ticket_slug}-{datetime.now().strftime('%Y%m%d%H%M')}"

    returncode, stdout, stderr = run_cmd(f"git checkout -b {branch_name}", repo_path)
    if returncode != 0:
        raise Exception(f"Failed to create branch: {stderr}")

    return branch_name


def write_and_stage_files(repo_path: str, changed_files: list) -> None:
    for file in changed_files:
        full_path = os.path.join(repo_path, file['path'])
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if file.get('action') == 'create':
            with open(full_path, 'w') as f:
                f.write(file['new_str'])
        # for modify — file already written by apply_all_changes_for_file
        # just stage it
        run_cmd(f"git add {file['path']}", repo_path)


def commit_changes(repo_path: str, commit_message: str) -> str:
    returncode, stdout, stderr = run_cmd(
        f'git commit -m "{commit_message}"',
        repo_path
    )
    if returncode != 0:
        raise Exception(f"Failed to commit: {stderr}")

    _, commit_hash, _ = run_cmd("git rev-parse --short HEAD", repo_path)
    return commit_hash


def get_diff(repo_path: str) -> str:
    _, diff, _ = run_cmd("git diff HEAD~1 HEAD", repo_path)
    return diff


def clone_or_pull(repo_url: str, local_path: str) -> None:
    if os.path.exists(local_path):
        print(f"repo exists, pulling latest...")
        run_cmd("git checkout master", local_path)
        returncode, stdout, stderr = run_cmd("git pull origin master", local_path)
        if returncode != 0:
            raise Exception(f"git pull failed: {stderr}")
        print(f"✓ pulled latest")
    else:
        print(f"cloning {repo_url}...")
        result = subprocess.run(
            f"git clone {repo_url} {local_path}",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"git clone failed: {result.stderr}")
        print(f"✓ cloned to {local_path}")