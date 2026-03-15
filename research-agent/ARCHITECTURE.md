# Research Agent — Architecture & Code Flow

## High-level Architecture

```
User (CLI or Browser)
    |
    v
+---------------+     +-------------+     +----------------+
|  main.py      |     |  agent.py   |     |   tools.py     |
|  (CLI REPL)   |---->|  (ReAct     |---->|  web_search    |
|               |     |   agent)    |     |  read_url      |
|  app.py       |---->|             |<----|  write_report  |
|  (FastAPI)    |     +-------------+     +----------------+
+---------------+           |
                            v
                      +-------------+
                      |   OpenAI    |
                      |   GPT API   |
                      +-------------+
```

## Startup Flow

1. **`config.py`** loads first — reads `.env` via pydantic-settings, exposes `Settings` (API key, model name, limits) and the `SYSTEM_PROMPT` (instructions the LLM follows).

2. **`tools.py`** defines 3 functions decorated with `@tool`. LangChain extracts the function name + docstring and presents them to the LLM as available tools. The LLM never sees the Python code — only the name and docstring.

3. **`agent.py`** wires everything together at import time:
   - Creates a `ChatOpenAI` instance (the LLM)
   - Creates a `MemorySaver` (in-memory conversation history)
   - Calls `create_react_agent()` — this builds a LangGraph state machine implementing the **ReAct loop**

## The ReAct Loop (core logic)

This is the heart of the agent. Each user query triggers this cycle:

```
User message
    |
    v
+----------------------------------------------+
|  1. REASON -- LLM reads the conversation     |
|     history + tool descriptions and decides:  |
|     "Should I call a tool, or respond?"       |
|                                               |
|  2. ACT -- If tool needed, LLM outputs a     |
|     structured tool call (name + args).       |
|     LangGraph executes the tool function.     |
|                                               |
|  3. OBSERVE -- Tool result (string) is added  |
|     back into the conversation context.       |
|                                               |
|  4. REPEAT -- Go back to step 1.             |
|     LLM sees the tool result and decides      |
|     whether to call another tool or respond.  |
+----------------------------------------------+
    |
    v (when LLM decides it has enough info)
Final text response to user
```

A typical research query does ~5-8 cycles:

```
web_search("RAG approaches")          -> 5 results
web_search("sentence window RAG")     -> 5 results
read_url("https://best-article...")   -> 8000 chars of text
read_url("https://another-one...")    -> 8000 chars of text
web_search("RAG comparison 2026")     -> 5 results
write_report("rag_comparison", "# ...full markdown...")  -> saved to output/
```

The LLM decides what to search, which URLs to read, and when it has enough — no hardcoded sequence.

## Context Engineering

The key constraint is the LLM's context window. Every tool result goes back into the conversation, so:

- **`web_search`** returns only titles + snippets (not full pages)
- **`read_url`** truncates to 8000 chars (`max_url_content_length`)
- **`max_iterations=25`** caps the ReAct cycles so the agent can't loop forever

Without these limits, a few `read_url` calls could fill the entire context window.

## Two Interfaces, Same Agent

**`main.py` (CLI)** — simple REPL loop:

```
input() -> agent.stream() -> print chunks as they arrive -> loop
```

**`app.py` (FastAPI)** — web UI with SSE streaming. The tricky part:

`agent.stream()` is **synchronous** (blocks the thread), but FastAPI is **async**. The bridge:

```
Browser <-- SSE <-- async generator <-- asyncio.Queue <-- thread (agent.stream)
```

`_stream_response()` spins up a thread via `run_in_executor`, the thread runs `agent.stream()` and pushes chunks into a `Queue`, the async generator reads from the queue and yields SSE events. This prevents the agent from blocking FastAPI's event loop.

## Memory

`MemorySaver` + `thread_id` in the config. All messages (user, AI, tool calls, tool results) are stored keyed by `thread_id`. On the next turn, the full history is loaded and sent to the LLM — that's how follow-up questions work.

CLI uses `"session-1"`, web uses `"web-session"`. In-memory only — lost on restart.

## Docker

Multi-stage build to keep the image small:

```
Stage 1 (builder): python:3.12-slim + gcc -> pip install -> ~1.2 GB
Stage 2 (runtime): python:3.12-slim + COPY packages from stage 1 -> ~530 MB
```

gcc is needed to compile C extensions (trafilatura), but discarded in the final image. `docker-compose.yml` mounts `output/` and `logs/` so reports and logs persist on the host.

## File Summary

| File | Role |
|------|------|
| `config.py` | Settings from `.env` + system prompt |
| `tools.py` | 3 tool functions the LLM can call |
| `agent.py` | Assembles LLM + tools + memory into a ReAct agent |
| `main.py` | CLI REPL interface |
| `app.py` | FastAPI web UI with SSE |
| `Dockerfile` | Multi-stage container build |
