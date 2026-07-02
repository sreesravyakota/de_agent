import ast
import os
import re
from pathlib import Path


def get_python_files(repo_path: str) -> list[str]:
    py_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', 'node_modules']]
        for f in files:
            if f.endswith('.py') and '__init__' not in f:
                py_files.append(os.path.join(root, f))
    return py_files


def extract_ast_info(filepath: str) -> dict:
    with open(filepath) as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    info = {
        'classes': [],
        'functions': [],
        'imports': [],
        'task_ids': [],
        'tables': []
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            info['classes'].append(node.name)
        elif isinstance(node, ast.FunctionDef):
            info['functions'].append(node.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            info['imports'].append(node.module)

        elif isinstance(node, ast.keyword):
            if node.arg == 'task_id' and isinstance(node.value, ast.Constant):
                info['task_ids'].append(node.value.value)

        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value.strip()
            tables = re.findall(r'\b([a-zA-Z_]+\.[a-zA-Z_]+)\b', s)
            info['tables'].extend(tables)

    info['tables'] = list(set(info['tables']))
    return info


def build_ast_map(repo_path: str) -> dict:
    ast_map = {}
    for filepath in get_python_files(repo_path):
        rel_path = os.path.relpath(filepath, repo_path)
        info = extract_ast_info(filepath)
        if info:
            ast_map[rel_path] = info
    return ast_map


def build_file_table_map(ast_map: dict) -> dict:
    table_map = {}
    for filepath, info in ast_map.items():
        for table in info.get('tables', []):
            if table not in table_map:
                table_map[table] = []
            table_map[table].append(filepath)
    return table_map


def ast_map_to_markdown(ast_map: dict) -> str:
    lines = ['# AST Map\n']
    for filepath, info in ast_map.items():
        lines.append(f'## {filepath}')
        if info.get('classes'):
            lines.append(f"- classes: {', '.join(info['classes'])}")
        if info.get('functions'):
            lines.append(f"- functions: {', '.join(info['functions'])}")
        if info.get('task_ids'):
            lines.append(f"- dag_tasks: {', '.join(info['task_ids'])}")
        if info.get('tables'):
            lines.append(f"- tables: {', '.join(info['tables'])}")
        if info.get('imports'):
            lines.append(f"- imports: {', '.join(info['imports'])}")
        lines.append('')
    return '\n'.join(lines)


def file_table_map_to_markdown(file_table_map: dict) -> str:
    lines = ['# File → Table Map\n']
    for table, files in sorted(file_table_map.items()):
        lines.append(f'## {table}')
        for f in files:
            lines.append(f'  - {f}')
        lines.append('')
    return '\n'.join(lines)