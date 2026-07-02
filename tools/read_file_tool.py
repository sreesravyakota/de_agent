from langchain_core.tools import tool
from typing import Optional
import os


@tool
def read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """Read a file from the repo with line numbers. 
    If no start/end given, reads lines 1-200.
    
    Args:
        path: relative path to file from repo root
        start_line: line to start reading from
        end_line: line to stop reading at
    """
    from tools.context import get_repo_path
    repo_path = get_repo_path()
    
    full_path = os.path.join(repo_path, path)
    
    if not os.path.exists(full_path):
        return f"File not found: {path}"
    
    with open(full_path, 'r') as f:
        all_lines = f.readlines()
    
    total_lines = len(all_lines)
    
    if start_line is None:
        start_line = 1
    if end_line is None:
        end_line = min(start_line + 199, total_lines)
    
    start_line = max(1, start_line)
    end_line = min(end_line, total_lines)
    
    sliced = all_lines[start_line - 1:end_line]
    
    numbered = []
    for i, line in enumerate(sliced, start=start_line):
        numbered.append(f"{i:4d}  {line}")
    
    header = f"[{path} | lines {start_line}-{end_line} of {total_lines}]"
    
    if end_line < total_lines:
        footer = f"\n... {total_lines - end_line} more lines. call read_file with start_line={end_line + 1}"
    else:
        footer = ""
    
    return f"{header}\n\n{''.join(numbered)}{footer}"