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

Jira Ticket
↓
┌─────────────────────────────────────────────────────┐
│                   LangGraph Pipeline                 │
│                                                      │
│  ┌──────────────────┐                               │
│  │ Artifact Generator│  os.walk + Python AST        │
│  │                  │  → tree.md                    │
│  │                  │  → ast_map.md                 │
│  │                  │  → file_table_map.md           │
│  │                  │  → CLAUDE.md (via Claude API) │
│  └────────┬─────────┘                               │
│           ↓                                          │
│  ┌──────────────────┐                               │
│  │ Discovery Agent  │  Tool-calling agent           │
│  │                  │  Tools: grep_repo, read_file  │
│  │                  │  → discovery_summary          │
│  └────────┬─────────┘                               │
│           ↓                                          │
│  ┌──────────────────┐                               │
│  │   Plan Node      │  Structured output via        │
│  │                  │  tool_use (submit_plan)       │
│  │                  │  Pydantic validation          │
│  │                  │  ← HITL approval gate →       │
│  └────────┬─────────┘                               │
│           ↓ (if approved)                            │
│  ┌──────────────────┐                               │
│  │ Developer Node   │  Atomic str_replace           │
│  │                  │  Self-healing retry           │
│  │                  │  git branch + commit          │
│  └──────────────────┘                               │
└─────────────────────────────────────────────────────┘
↓
Git Branch + MR Description

---

## AI & Agentic Concepts

### Artifact Generation
- `os.walk` + Python `ast` module parses every `.py` file in the repo
- Extracts classes, functions, task_ids, table references
- Builds a file→table map and inverted table→file map
- Claude actively explores the repo with tools to generate `CLAUDE.md`
- Same pattern as Claude Code's `/init` command

### Tool-Calling Discovery Agent
- Bounded tool-call loop (max 15 calls)
- Tools: `grep_repo` (subprocess grep) and `read_file` (line-numbered)
- Claude autonomously decides what to read based on the ticket
- Produces a discovery summary with exact line numbers and verbatim code snippets
- Context injection via `tools/context.py` — repo path set globally

### Structured Output with Pydantic
- Plan node forces Claude to call `submit_plan` tool via `tool_choice`
- Output validated against Pydantic schema at parse time
- `Plan → list[FileChange] → list[Change(old_str, new_str, why)]`
- Developer node reads typed objects directly — no regex parsing

### str_replace Pattern
- Same technique used by Claude Code
- Each change specifies exact `old_str` to find and `new_str` to replace
- Applied atomically in memory per file — read once, apply all changes, write once
- Self-healing retry: if `old_str` fails, Claude reads actual file and corrects it

### Human-in-the-Loop (HITL)
- Plan presented to human before any file is touched
- Approve / edit with feedback / reject
- Edit triggers plan revision with full conversation history
- Mapped to "plan gate" in production agentic architectures

### Validation Gates
- Pre-flight: all file paths verified against `tree.md` before HITL
- Auto-retry with feedback if files not found (max 3 retries)
- Dry-run: `old_str` verified before apply
- Retry mechanism: Claude fixes failed str_replace by reading actual file

### LangGraph Orchestration
- 4 nodes wired as a state machine
- Typed state (`AgentState` TypedDict) flows through all nodes
- Conditional edge after plan — approved → developer, rejected → END
- MemorySaver checkpointer for resumable workflows
- `thread_id` enables replay from any checkpoint

---

## Project Structure
de_agent/
├── main.py                    # entry point — runs the LangGraph pipeline
├── graph.py                   # LangGraph graph definition
├── state.py                   # AgentState TypedDict
├── models.py                  # Pydantic models (Plan, FileChange, Change)
│
├── nodes/
│   ├── artifact_generator.py  # os.walk + AST + CLAUDE.md generation
│   ├── discovery.py           # tool-calling discovery agent
│   ├── plan.py                # structured output + HITL
│   └── developer.py          # str_replace + git operations
│
├── tools/
│   ├── grep_tool.py           # grep_repo tool (@tool decorator)
│   ├── read_file_tool.py      # read_file tool with line numbers
│   └── context.py             # global repo_path injection
│
├── utils/
│   ├── ast_parser.py          # AST extraction, file-table mapping
│   └── git_utils.py           # branch, commit, diff, clone/pull
│
└── artifacts/                 # generated at runtime (gitignored)
├── tree.md
├── ast_map.md
├── file_table_map.md
└── CLAUDE.md

---

## Tech Stack

- **LangGraph** — multi-node agent orchestration, state machine
- **Anthropic Claude** — claude-sonnet-4-6 for all agent nodes
- **LangChain** — tool decorators, message types, ChatAnthropic
- **Pydantic** — structured output validation
- **Python AST** — static code analysis
- **GitPython / subprocess** — git operations

---

## Test Repo

Tested against [san089/goodreads_etl_pipeline](https://github.com/san089/goodreads_etl_pipeline) — a realistic Airflow + Redshift + PySpark data engineering pipeline with:
- Custom Airflow operators
- Staging → warehouse → analytics schema pattern
- PySpark transforms on EMR
- SQL query files, DAG definitions, warehouse driver

---

## Results

**GR-101: Add ratings_summary table**
- 7 files modified across staging, warehouse, upsert, analytics, DAG
- PySpark transform + Redshift DDL + upsert + analytics + DAG tasks
- Applied with 0 retries on final run

**GR-102: Add author_stats summary table**  
- Agent correctly identified analytics-only change
- 2 files modified (vs 7 for GR-101)
- Skipped staging, warehouse DDL, upsert entirely
- Applied with 1 retry (self-healed)

---

## Production Mapping

This prototype maps directly to a production agentic DE architecture:

| Prototype | Production |
|---|---|
| Local git branch | GitLab MR with branch protection |
| CLI HITL | GitLab MR review gate |
| File system tools | GitLab API (search, read, blame) |
| `artifacts/CLAUDE.md` | ContextPack in durable state store |
| MemorySaver | Firestore / Cloud SQL state |
| Single process | Separate Cloud Run services per agent |
| Jira hardcoded | Jira webhook → Pub/Sub queue |

---

## Setup

```bash
git clone https://github.com/yourusername/de-agent
cd de-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# add your Anthropic API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# clone the test repo
git clone https://github.com/san089/goodreads_etl_pipeline \
  /path/to/goodreads_etl_pipeline

# update repo path in main.py
# then run
python main.py
```


