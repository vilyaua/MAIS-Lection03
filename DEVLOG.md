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

### 02:10 — Multi-provider support
- Added `PROVIDER` setting to `config.py` (`"openai"` or `"anthropic"`)
- Refactored `agent.py` with `_build_llm()` — lazy imports for `ChatOpenAI` / `ChatAnthropic`
- Updated `.env.example` with both providers and latest model recommendations (`gpt-4.1-mini`, `claude-sonnet-4-6`)
- Added `langchain-anthropic>=0.3.0` to `requirements.txt`

### 02:20 — Pre-commit setup
- Added `.pre-commit-config.yaml` with `pre-commit-hooks` (trailing whitespace, EOF fixer, YAML/TOML check, large files, merge conflicts, private key detection) and `ruff` (linter + formatter)
- Added `pyproject.toml` with ruff config: E, W, F, I, UP, B, SIM, S rule sets, line-length 100
- Ran `pre-commit run --all-files` — fixed trailing whitespace and EOF issues in `homework-lesson-3/`
- Installed hooks into `.git/hooks/pre-commit`

### 02:30 — Merged `feat/first-approach` into `main`

### 02:35 — Streamlit UI + Docker (`feat/docker`)
- Added `app.py` — Streamlit chat UI with real-time tool call status, token usage sidebar
- Added `Dockerfile` — `python:3.12-slim`, single-stage, healthcheck, exposes 8501
- Added `docker-compose.yml` — `.env` passthrough, `output/` volume mount
- Added `.dockerignore`
- Added `streamlit>=1.45.0` to `requirements.txt`
- Updated `README.md` — Docker as recommended setup, both web UI and console usage docs
