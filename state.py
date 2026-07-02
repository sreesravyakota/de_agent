from typing import TypedDict, Optional
from models import Plan


class AgentState(TypedDict):
    # inputs
    repo_path: str
    jira_ticket: str

    # artifact generator outputs
    tree_md: str
    ast_map_md: str
    file_table_map_md: str
    claude_md: str

    # discovery output
    discovery_summary: str

    # plan output
    plan: str
    plan_obj: Optional[Plan]
    plan_approved: bool
    plan_feedback: str

    # developer output
    changed_files: list[dict]
    branch_name: str
    commit_message: str
    mr_description: str