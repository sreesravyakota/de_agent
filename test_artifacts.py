import sys
sys.path.append(".")

from utils.git_utils import clone_or_pull
from nodes.artifact_generator import artifact_generator

clone_or_pull(
    repo_url="https://github.com/san089/goodreads_etl_pipeline",
    local_path="/Users/sravyakota/vscode_proj/goodreads_etl_pipeline"
)

state = {
    "repo_path": "/Users/sravyakota/vscode_proj/goodreads_etl_pipeline",
    "jira_ticket": "",
    "tree_md": "",
    "ast_map_md": "",
    "file_table_map_md": "",
    "claude_md": "",
    "discovery_summary": "",
    "plan": "",
    "plan_approved": False,
    "plan_feedback": "",
    "changed_files": [],
    "branch_name": "",
    "commit_message": "",
    "mr_description": ""
}

print("starting artifact generator...\n")
result = artifact_generator(state)

print("\n--- TREE.MD ---")
print(result["tree_md"][:500])
print("\n--- AST MAP ---")
print(result["ast_map_md"][:500])
print("\n--- FILE TABLE MAP ---")
print(result["file_table_map_md"][:500])
print("\n--- CLAUDE.MD ---")
print(result["claude_md"][:1000])
print("\ndone.")