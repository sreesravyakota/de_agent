import sys
sys.path.append(".")

from utils.git_utils import clone_or_pull
from nodes.artifact_generator import artifact_generator
from nodes.discovery import discovery
from nodes.plan import plan

clone_or_pull(
    repo_url="https://github.com/san089/goodreads_etl_pipeline",
    local_path="/Users/sravyakota/vscode_proj/goodreads_etl_pipeline"
)

state = {
    "repo_path": "/Users/sravyakota/vscode_proj/goodreads_etl_pipeline",
    "jira_ticket": """
GR-101: Add ratings_summary table

Add a new ratings_summary table that aggregates average rating 
and total review count per author from the reviews table.

Staging table: goodreads_staging.ratings_summary
Warehouse table: goodreads_warehouse.ratings_summary

Columns:
- author_id BIGINT
- avg_rating FLOAT
- total_reviews INT
- record_create_timestamp TIMESTAMP

Follow all existing patterns. Add to existing DAG quality checks.
""",
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

print("running artifact generator...")
state = artifact_generator(state)

print("\nrunning discovery...")
state = discovery(state)

print("\nrunning plan...")
state = plan(state)

if state["plan_approved"]:
    print("\nplan approved — ready for developer node")
else:
    print("\nplan rejected — stopping")