# DE Agent — Agentic Data Engineering Pipeline

An end-to-end agentic AI system that reads a Jira ticket, understands 
a data engineering codebase, plans implementation changes with human 
approval, and creates a git branch with validated code changes.

Built as a proof-of-concept prototype mapping to a production 
agentic data engineering architecture.

---

## Use Case

Data engineering teams spend significant time on repetitive 
implementation work — adding new tables, wiring DAG tasks, writing 
boilerplate SQL. This agent automates that loop:

1. Engineer creates a Jira ticket: "Add a ratings_summary table"
2. Agent reads the ticket and explores the codebase
3. Agent proposes an implementation plan for human review
4. Engineer approves, edits, or rejects the plan
5. Agent applies changes and creates a git branch with a commit

The human stays in control at the approval gate — the agent handles 
the discovery and implementation work.

---

## Architecture