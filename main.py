import sys
sys.path.append(".")

from utils.git_utils import clone_or_pull
from graph import app

REPO_URL = "https://github.com/san089/goodreads_etl_pipeline"
REPO_PATH = "/Users/sravyakota/vscode_proj/goodreads_etl_pipeline"

JIRA_TICKET = """
GR-102: Add author_stats summary table

We need a new author_stats table that provides a comprehensive 
view of author performance metrics.

This is a DERIVED/AGGREGATED table computed from existing 
warehouse tables. No raw S3 source file.

Warehouse table: goodreads_warehouse.author_stats

Columns:
- author_id BIGINT
- author_name VARCHAR
- total_books INT
- total_reviews INT  
- avg_book_rating FLOAT
- record_create_timestamp TIMESTAMP

This table joins goodreads_warehouse.authors with 
goodreads_warehouse.reviews and goodreads_warehouse.books
to produce a single comprehensive author view.

It should be added to the analytics layer and DAG following 
all existing patterns. No staging table needed — compute 
directly in the upsert step from warehouse tables.
"""

def main():
    clone_or_pull(repo_url=REPO_URL, local_path=REPO_PATH)

    initial_state = {
        "repo_path": REPO_PATH,
        "jira_ticket": JIRA_TICKET,
        "tree_md": "",
        "ast_map_md": "",
        "file_table_map_md": "",
        "claude_md": "",
        "discovery_summary": "",
        "plan": "",
        "plan_obj": None,
        "plan_approved": False,
        "plan_feedback": "",
        "changed_files": [],
        "branch_name": "",
        "commit_message": "",
        "mr_description": ""
    }

    config = {"configurable": {"thread_id": "gr-101"}}

    print("="*60)
    print("DE AGENT — starting pipeline")
    print("="*60)

    final_state = app.invoke(initial_state, config=config)

    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)

    if final_state.get("branch_name"):
        print(f"branch:  {final_state['branch_name']}")
        print(f"commit:  {final_state['commit_message']}")
        print(f"\n--- MR DESCRIPTION ---")
        print(final_state["mr_description"])
    else:
        print("pipeline stopped — plan was rejected or no changes applied")


if __name__ == "__main__":
    main()