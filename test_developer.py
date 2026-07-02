import sys
sys.path.append(".")

from utils.git_utils import clone_or_pull
from nodes.artifact_generator import artifact_generator
from nodes.discovery import discovery
from nodes.plan import plan
from nodes.developer import developer

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

NOTE: This is a DERIVED/AGGREGATED table — not a raw entity table.
It has no S3 source file. It must follow existing staging patterns
with a PySpark transform writing to S3 processed zone.

Staging table: goodreads_staging.ratings_summary
Warehouse table: goodreads_warehouse.ratings_summary
Analytics table: goodreads_analytics.ratings_summary

Columns:
- author_id BIGINT
- avg_rating FLOAT
- total_reviews INT
- record_create_timestamp TIMESTAMP

Follow all existing patterns. Add to existing DAG with quality checks.
""",
    "tree_md": "",
    "ast_map_md": "",
    "file_table_map_md": "",
    "claude_md": "",
    "discovery_summary": "",
    "plan": "",
    "plan_json": {},
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

# debug print after plan
if state.get("plan_obj"):
    plan_obj = state["plan_obj"]
    print("\n--- PLAN OBJ (debug) ---")
    print(f"files: {[f.path for f in plan_obj.files]}")
    print(f"total changes: {sum(len(f.changes) for f in plan_obj.files)}")
    for f in plan_obj.files:
        print(f"  {f.path}: {len(f.changes)} change(s)")
else:
    print("\n⚠️  plan_obj is None")

if state["plan_approved"]:
    print("\nrunning developer...")
    state = developer(state)
    print("\n--- MR DESCRIPTION ---")
    print(state["mr_description"])
else:
    print("\nplan not approved — stopping")