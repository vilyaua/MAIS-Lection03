# Development Log

## 2026-03-15

### 01:38 — Project scaffolding
- Cloned `homework-lesson-3/` skeleton (stubs for `agent.py`, `tools.py`, `config.py`, `main.py`)
- Created `AGENTS.md` — implementation guide with steps, code examples, and checklist

### 01:45 — First implementation (`research-agent/`)
- Implemented `tools.py`: `web_search` (ddgs), `read_url` (trafilatura + truncation), `write_report`
- Implemented `agent.py`: `create_react_agent` with `ChatOpenAI`, `MemorySaver`
- Implemented `main.py`: interactive REPL with `thread_id` for memory, `recursion_limit`
- Implemented `config.py`: `Settings` (pydantic-settings) + `SYSTEM_PROMPT`
- Added `requirements.txt`, `.env.example`, `.gitignore`, `README.md`
- Copied example report to `example_output/report.md`

### 01:50 — Git setup
- Committed `AGENTS.md` + `homework-lesson-3/` to `main` branch as "initial commit"
- Created `feat/first-approach` branch with `research-agent/` + updated `README.md`
- Pushed both to remote

### 02:00 — Added persona, guardrails, and logging to AGENTS.md
- Added **Persona** section ("seasoned Python/AI developer")
- Added **Guardrails** (keep it simple, follow requirements exactly, no abstractions, test before commit)
- Added **Step 5: Logging & Token Usage Tracking** (per-turn + cumulative session tokens, tool call logging)
- Updated checklist with logging items
- Updated `research-agent/main.py` to match: `logging` module, `usage_metadata` tracking, tool call tracing
