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

### 03:00 — File logging, versioning, provider/model display
- Added `VERSION` file (single source of truth: `0.1.0`)
- `config.py`: reads `APP_VERSION` from `VERSION` file
- `Dockerfile`: `ARG APP_VERSION` stamped into `VERSION` at build time
- `docker-compose.yml`: passes `APP_VERSION` build arg, mounts `logs/` volume
- `app.py`: sidebar shows version, provider, model; live-updating token metrics; descriptive tool status (result count, chars extracted, errors); logs to `logs/agent.log` (rotating 5MB)
- `main.py`: prints version/provider/model on startup; descriptive tool status; file logging
- `.gitignore`: added `logs/`

### 04:00 — Multi-stage Dockerfile + report improvements
- `Dockerfile`: refactored to multi-stage build (builder + runtime) — image size reduced from 1.19GB to 934MB by discarding gcc/build toolchain
- `tools.py`: `write_report` — renamed `filename` param to `description`; auto-generates filename as `YYYY-MM-DD_HHMM_<description>.md`; prepends metadata line with provider and model name to report content

### 04:30 — Log user requests
- `app.py`, `main.py`: log every user query and session exit to `logs/agent.log`

### 05:00 — Refactor to FastAPI (`feat/fast-api`)
- Replaced Streamlit with FastAPI + inline HTML/JS chat UI with SSE streaming
- Endpoints: `GET /` (chat UI), `GET /api/info` (version/provider/model), `GET /api/chat?q=` (SSE stream)
- Replaced `streamlit>=1.45.0` with `fastapi>=0.115.0` + `uvicorn>=0.34.0`
- Dockerfile: entrypoint `streamlit` → `uvicorn`, port 8501 → 8000
- Expected image size: ~934MB → ~530MB (removed pyarrow, pandas, numpy, babel, pydeck, altair)
- Bumped VERSION: 0.1.0 → 0.2.0

### 05:30 — Fix session hanging
- `tools.py`: added 10s download timeout to `trafilatura.fetch_url` — was hanging indefinitely on slow/unresponsive URLs
- `app.py`: wrapped sync `agent.stream()` in a thread via `asyncio.Queue` + `run_in_executor` — prevents blocking FastAPI's event loop
- Bumped VERSION: 0.2.0 → 0.2.1

### 06:00 — Fix missing output files
- `config.py`: strengthened system prompt — `write_report` is now mandatory ("ALWAYS call write_report as your final tool call"), updated param name from `filename` to `description`
- Root cause: LLM was skipping `write_report` and giving direct answers instead of saving reports
- Bumped VERSION: 0.2.1 → 0.2.2

### 06:10 — OpenAI-only: remove Anthropic support
- Removed `_build_llm()` factory in `agent.py` — direct `ChatOpenAI` instantiation
- Removed `provider` field from `config.py` Settings
- Removed `langchain-anthropic` from `requirements.txt`
- Cleaned up `tools.py`, `main.py`, `app.py` — removed all `settings.provider` references
- Simplified `.env.example` — OpenAI only, no provider switching
- Updated `README.md` — removed `PROVIDER` env var row
- Updated `AGENTS.md` — removed multi-provider notes
- Bumped VERSION: 0.2.2 → 0.3.0

### 06:15 — Add code comments for mid-level developers
- Added module docstrings to `agent.py`, `tools.py`, `main.py`, `app.py`
- Commented non-obvious patterns: SecretStr unwrapping, MemorySaver purpose, ReAct loop, context engineering truncation, sync-to-async bridge via Queue, multi-stage Docker build rationale
- Added inline comments to `config.py` (max_url_content_length, max_iterations)
- Added comments to `Dockerfile` and `docker-compose.yml`

### 06:18 — Show tool call arguments in UI and CLI
- `app.py`, `main.py`: capture `tool_calls` args from AIMessage, buffer in `pending_calls`, pair with tool results via `tool_call_id`
- Added `_get_tool_call_args()` helper (shared pattern in both files)
- Web UI now shows: `→ web_search("RAG approaches") — 5 results found`
- CLI now shows: `[web_search]("RAG approaches") — 5 results found`
- Added `ARCHITECTURE.md` — full code flow and architecture explanation
- Bumped VERSION: 0.3.0 → 0.3.1

### 06:19 — Error handling for LLM and agent failures
- `main.py`, `app.py`: wrapped `agent.stream()` with try/except for:
  - `GraphRecursionError` — max ReAct iterations exceeded
  - `APIError`, `APIConnectionError`, `RateLimitError`, `AuthenticationError` — OpenAI failures
  - Generic `Exception` fallback
- CLI: prints friendly error, logs details, continues REPL (no crash)
- Web UI: sends error as SSE message event so user sees it in chat
- Tools were already safe (`except Exception` → error string) — gap was only around the agent loop
- Bumped VERSION: 0.3.1 → 0.3.2

### 06:25 — Add list_reports and read_file tools
- `tools.py`: added `list_reports()` — lists saved .md files in output/ (newest first)
- `tools.py`: added `read_file(filename)` — reads a report from output/ with path traversal protection
- `agent.py`: registered both tools in the agent's tool list
- `config.py`: updated system prompt with tool descriptions
- `main.py`, `app.py`: added display formatting for new tools in CLI and SSE
- Both tools reuse `max_url_content_length` truncation for context engineering
- Bumped VERSION: 0.3.2 → 0.4.0

### 06:30 — Reports panel in web UI
- `app.py`: added `GET /api/reports` (list reports as JSON) and `GET /api/reports/{filename}` (serve raw markdown)
- Path traversal protection on `/api/reports/{filename}`
- Sidebar: added "Reports" section — loads on page load, refreshes after each query completes
- Each report is a clickable link that opens raw markdown in a new tab
- Bumped VERSION: 0.4.0 → 0.4.1

### 06:35 — Track generated reports in git
- Removed `output/` from `.gitignore` — agent-generated reports are now committed
- Added 8 existing reports to the repo

### 06:45 — Filter & sort reports descending
- `app.py`: `/api/reports` now filters to only date-prefixed filenames (`f.name[:1].isdigit()`) and sorts descending (newest first)
- Bumped VERSION: 0.4.2 → 0.4.3

### 06:40 — Alphabetical reports + colorful tool logs
- `app.py`: `/api/reports` now sorts files alphabetically by name instead of by modification time
- `app.py`: added per-tool CSS color classes — `web_search` (blue), `read_url` (purple), `write_report` (green), `list_reports` (amber), `read_file` (cyan)
- `app.py`: `addTool()` JS function accepts tool name and applies matching color class
- Bumped VERSION: 0.4.1 → 0.4.2

### 06:20 — Fix Docker version mismatch
- Removed `ARG APP_VERSION` from Dockerfile and build args from docker-compose.yml
- `VERSION` file is now the single source of truth — `COPY . .` brings it into the image, `config.py` reads it
- Was showing `0.1.0` in Docker because docker-compose fallback was hardcoded
