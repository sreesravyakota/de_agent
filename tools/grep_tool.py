from langchain_core.tools import tool
from typing import Optional
import subprocess


@tool
def grep_repo(pattern: str, file_pattern: Optional[str] = "*.py") -> str:
    """Search the repo for a pattern. Returns file paths and line numbers of matches.
    
    Args:
        pattern: the pattern to search for
        file_pattern: file glob to search in e.g. *.py, *.sql. defaults to *.py
    """
    # repo_path injected at runtime via closure
    from tools.context import get_repo_path
    repo_path = get_repo_path()
    
    cmd = f'grep -rn --include="{file_pattern}" "{pattern}" .'
    
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 1:
        return f"No matches found for pattern: {pattern}"
    if result.returncode > 1:
        return f"grep error: {result.stderr}"
    
    lines = result.stdout.strip().split('\n')
    if len(lines) > 50:
        lines = lines[:50]
        lines.append("... truncated, narrow your pattern")
    
    return '\n'.join(lines)