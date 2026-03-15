# AGENTS.md — Research Agent (Lesson 3 Homework)

## Persona

You are a **seasoned Python/AI developer** with deep experience in LangChain, LangGraph, and building LLM-powered agents. You write clean, minimal, production-aware code.

## Guardrails

- **Keep it simple.** Use `create_react_agent` directly — no custom abstractions, factory patterns, or wrapper classes. The homework asks for a ReAct agent, not a framework.
- **Follow homework requirements exactly.** Implement what's specified — 3 tools, agent loop, memory, context engineering. Don't add features that weren't asked for.
- **Don't invent abstractions.** No base classes, no tool registries, no plugin systems. Three functions decorated with `@tool` is enough.
- **Test before committing.** Run `python main.py`, ask a real question, verify the agent calls multiple tools and produces a report.
- **Handle errors in tools, not in the agent loop.** Each tool returns a string — on failure, return a clear error message. The agent (LLM) will adapt.
- **Secrets stay in `.env`.** Never hardcode API keys. Never commit `.env`.

## Work Tracking

After every significant change (new feature, bugfix, refactor, config change), append an entry to `DEVLOG.md` with:
- **Date and time** (YYYY-MM-DD HH:MM)
- **Short title** describing what was done
- **Bullet list** of concrete changes (files touched, what changed, why)

Keep entries factual and concise. Don't log trivial edits (typo fixes, formatting). Group related changes into one entry.

## Goal

Build an interactive **Research Agent** that takes a user's question, autonomously searches the web using tools, collects findings, and generates a structured Markdown report — all powered by LangChain's ReAct agent loop.

## Source & Destination

- **Source (skeleton):** `homework-lesson-3/` — original homework template with stubs and task description
- **Destination (implementation):** `research-agent/` — completed project with all code

## Project Structure

```
research-agent/
├── main.py              # Entry point — interactive REPL loop
├── agent.py             # Agent setup (LLM, tools, memory, create_react_agent)
├── tools.py             # Tool definitions and implementations
├── config.py            # System prompt, settings, constants
├── requirements.txt     # Pinned dependencies
├── .env                 # API keys (never commit)
├── .env.example         # Template for .env
├── .gitignore           # Excludes .env, output/, __pycache__/
├── example_output/
│   └── report.md        # Example generated report
├── output/              # Directory where agent saves reports
└── README.md            # Setup instructions, architecture overview
```

---

## Implementation Steps

### Step 1: Configure Environment (`config.py`)

The skeleton already has a `Settings` class using `pydantic-settings`. Complete it:

- `api_key` — LLM provider API key (read from `.env`)
- `model_name` — model identifier (e.g. `"gpt-4o-mini"`, `"claude-sonnet-4-20250514"`)
- `max_search_results` — default `5`
- `max_url_content_length` — default `5000`–`10000` characters (context engineering)
- `output_dir` — default `"output"`
- `max_iterations` — default `10` (safety limit for agent loop)

Write the **SYSTEM_PROMPT** in `config.py`. It must clearly describe:
1. The agent's role: "You are a research agent that investigates topics using web search and URL reading"
2. Available tools and when to use each one
3. Research strategy: search first, read promising URLs for details, then compile a structured Markdown report with sources
4. Output expectations: use `write_report` to save the final report to a file
5. Instruction to cite sources with URLs

### Step 2: Implement Tools (`tools.py`)

Use LangChain's `@tool` decorator for each function. Each tool must have a clear docstring (this becomes the tool description for the LLM).

#### 2.1 `web_search(query: str) -> str`

- Use `ddgs` library: `from ddgs import DDGS`
- Call `DDGS().text(query, max_results=settings.max_search_results)`
- Return a formatted string (not raw dict) with `title`, `url`, `snippet` for each result
- Handle exceptions gracefully — return an error message string, never crash

```python
from langchain_core.tools import tool
from ddgs import DDGS
from config import Settings

settings = Settings()

@tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo. Returns titles, URLs and snippets."""
    try:
        results = DDGS().text(query, max_results=settings.max_search_results)
        if not results:
            return "No results found."
        formatted = []
        for r in results:
            formatted.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n")
        return "\n---\n".join(formatted)
    except Exception as e:
        return f"Search error: {e}"
```

#### 2.2 `read_url(url: str) -> str`

- Use `trafilatura` to fetch and extract clean text
- **Truncate** the result to `settings.max_url_content_length` characters (context engineering — prevents flooding the context window)
- Handle errors: invalid URL, timeout, unreachable page

```python
import trafilatura

@tool
def read_url(url: str) -> str:
    """Fetch and extract the main text content from a web page URL."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return f"Error: Could not fetch URL: {url}"
        text = trafilatura.extract(downloaded)
        if not text:
            return f"Error: Could not extract text from: {url}"
        if len(text) > settings.max_url_content_length:
            text = text[:settings.max_url_content_length] + "\n\n[... truncated]"
        return text
    except Exception as e:
        return f"Error reading URL: {e}"
```

#### 2.3 `write_report(filename: str, content: str) -> str`

- Create `output/` directory if it doesn't exist
- Write Markdown content to `output/{filename}`
- Return confirmation with full path

```python
import os

@tool
def write_report(filename: str, content: str) -> str:
    """Save a Markdown research report to a file."""
    try:
        os.makedirs(settings.output_dir, exist_ok=True)
        filepath = os.path.join(settings.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Report saved to: {filepath}"
    except Exception as e:
        return f"Error saving report: {e}"
```

#### 2.4 Optional Extra Tools

Additional tools that can improve the grade if they are meaningful:
- `calculate(expression: str) -> str` — evaluate math expressions
- `read_file(filepath: str) -> str` — read a local file
- `list_files(directory: str) -> str` — list files in a directory

### Step 3: Build the Agent (`agent.py`)

Use LangChain's `create_react_agent` from `langgraph`.

```python
from langchain_openai import ChatOpenAI          # or ChatAnthropic, etc.
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from tools import web_search, read_url, write_report
from config import Settings, SYSTEM_PROMPT

settings = Settings()

llm = ChatOpenAI(
    model=settings.model_name,
    api_key=settings.api_key.get_secret_value(),
)

tools = [web_search, read_url, write_report]

memory = MemorySaver()

agent = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    prompt=SYSTEM_PROMPT,
)
```

Key requirements:
- **Memory**: `MemorySaver` enables multi-turn conversation within a session
- **Max iterations**: set `recursion_limit` when invoking to prevent infinite loops
- **Error handling**: if a tool returns an error string, the agent sees it in context and can adapt (retry with different params or skip)

### Step 4: Interactive REPL (`main.py`)

The skeleton is mostly complete. Key additions needed:

- Pass a `config` dict with `thread_id` to maintain conversation memory across turns
- Pass `recursion_limit` to cap agent iterations
- Stream agent responses for real-time output
- **Log token usage** after each turn (see Step 5)

```python
from agent import agent
from config import Settings

settings = Settings()

def main():
    print("Research Agent (type 'exit' to quit)")
    print("-" * 40)

    config = {
        "configurable": {"thread_id": "session-1"},
        "recursion_limit": settings.max_iterations,
    }

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        for chunk in agent.stream(
            {"messages": [("user", user_input)]},
            config=config,
        ):
            if "agent" in chunk and "messages" in chunk["agent"]:
                for msg in chunk["agent"]["messages"]:
                    if hasattr(msg, "content") and msg.content:
                        print(f"\nAgent: {msg.content}")
                    # Log token usage from each LLM response
                    if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                        u = msg.usage_metadata
                        logger.info(
                            "Tokens — input: %d, output: %d, total: %d",
                            u.get("input_tokens", 0),
                            u.get("output_tokens", 0),
                            u.get("total_tokens", 0),
                        )

if __name__ == "__main__":
    main()
```

### Step 5: Logging & Token Usage Tracking

Set up Python's built-in `logging` module to trace agent activity and token consumption. This is essential for debugging and cost awareness.

#### 5.1 Logger Setup

Configure logging at the top of `main.py` (or in a shared module):

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("research_agent")
```

#### 5.2 Token Tracking via `usage_metadata`

LangChain's `AIMessage` objects include a `usage_metadata` dict with token counts after each LLM call. Extract it while streaming:

```python
# Inside the stream loop, after checking msg.content:
if hasattr(msg, "usage_metadata") and msg.usage_metadata:
    u = msg.usage_metadata
    logger.info(
        "Tokens — input: %d, output: %d, total: %d",
        u.get("input_tokens", 0),
        u.get("output_tokens", 0),
        u.get("total_tokens", 0),
    )
```

#### 5.3 Cumulative Session Totals

Track total tokens across the entire session to understand cost:

```python
session_tokens = {"input": 0, "output": 0, "total": 0}

# Inside the stream loop, when usage_metadata is found:
session_tokens["input"] += u.get("input_tokens", 0)
session_tokens["output"] += u.get("output_tokens", 0)
session_tokens["total"] += u.get("total_tokens", 0)

# After each agent turn completes:
logger.info("Session totals — input: %d, output: %d, total: %d",
            session_tokens["input"], session_tokens["output"], session_tokens["total"])
```

#### 5.4 Tool Call Logging

Log which tools the agent calls to trace reasoning:

```python
# Inside the stream loop:
if "tools" in chunk and "messages" in chunk["tools"]:
    for msg in chunk["tools"]["messages"]:
        logger.info("Tool [%s]: %s", msg.name, msg.content[:200])
```

#### Why This Matters

- **Cost awareness** — know how many tokens each research query burns
- **Debugging** — see which tools fired, in what order, and what they returned
- **Context engineering validation** — verify that `read_url` truncation keeps token counts reasonable
- Use `logging` (not `print`) so output can be silenced or redirected without changing code

### Step 6: Dependencies (`requirements.txt`)

> Note: Steps 6–9 were originally numbered 5–8. Renumbered after inserting Step 5 (Logging).

```
langchain>=1.2.0
langchain-openai>=0.3.0
langgraph>=0.4.0
ddgs>=7.0
trafilatura>=2.0.0
pydantic>=2.12.0
pydantic-settings>=2.12.0
```

Add provider-specific packages as needed:
- `langchain-anthropic` for Claude
- `langchain-google-genai` for Gemini

### Step 7: `.env` File

Copy `.env.example` to `.env` and fill in real values:

```
API_KEY=sk-your-real-key
MODEL_NAME=gpt-4o-mini
```

### Step 8: Update `README.md`

Write a README covering:
1. **What it does** — one-paragraph description
2. **Setup** — `pip install -r requirements.txt`, copy `.env.example` to `.env`, add API key
3. **Usage** — `python main.py`, example queries
4. **Architecture** — brief description of agent loop, tools, memory
5. **Example output** — reference `example_output/report.md`

### Step 9: Generate Example Output

Run the agent with a real query (e.g., "Compare three RAG approaches: naive, sentence-window, and parent-child retrieval") and save the generated report to `example_output/report.md`.

---

## Checklist

- [ ] **3+ tools** implemented with `@tool` decorator and clear docstrings
- [ ] **`web_search`** uses `ddgs`, returns formatted results
- [ ] **`read_url`** uses `trafilatura`, truncates to N chars (context engineering)
- [ ] **`write_report`** saves Markdown to `output/` directory
- [ ] **Agent loop** uses `create_react_agent` from LangGraph
- [ ] **Memory** via `MemorySaver` — agent remembers conversation context
- [ ] **Agent autonomy** — agent decides which tools to call and in what order
- [ ] **Multi-step** — agent makes 3-5+ tool calls per query
- [ ] **Max iterations** — `recursion_limit` prevents infinite loops
- [ ] **Error handling** — tools return error strings, agent adapts
- [ ] **Logging** — `logging` module configured, not bare `print` for diagnostics
- [ ] **Token tracking** — per-turn and cumulative session token counts via `usage_metadata`
- [ ] **Tool call logging** — log tool names and truncated results for traceability
- [ ] **System prompt** in `config.py`, not hardcoded in agent logic
- [ ] **`.env`** for secrets, never committed (`.gitignore` covers it)
- [ ] **`requirements.txt`** with pinned versions
- [ ] **`README.md`** with setup and usage instructions
- [ ] **`example_output/report.md`** — one real generated report

## Expected Agent Behavior

```
User: "Compare naive RAG vs sentence-window retrieval"

Agent thinks: I need to research both approaches
  → web_search("naive RAG pipeline approach")
  → web_search("sentence window retrieval RAG")
  → read_url("https://some-relevant-article.com/...")
  → read_url("https://another-article.com/...")
  → web_search("naive vs sentence window RAG comparison tradeoffs")
  → write_report("rag_comparison.md", "# RAG Comparison\n\n...")

Agent: "I've completed the research and saved a detailed comparison
        report to output/rag_comparison.md. Here's a summary: ..."
```

The agent must autonomously chain multiple searches, read relevant pages for deeper context, synthesize findings, and save a structured report — all without hardcoded tool-call sequences.
