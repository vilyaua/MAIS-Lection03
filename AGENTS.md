# AGENTS.md — Research Agent (Lesson 3 Homework)

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

if __name__ == "__main__":
    main()
```

### Step 5: Dependencies (`requirements.txt`)

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

### Step 6: `.env` File

Copy `.env.example` to `.env` and fill in real values:

```
API_KEY=sk-your-real-key
MODEL_NAME=gpt-4o-mini
```

### Step 7: Update `README.md`

Write a README covering:
1. **What it does** — one-paragraph description
2. **Setup** — `pip install -r requirements.txt`, copy `.env.example` to `.env`, add API key
3. **Usage** — `python main.py`, example queries
4. **Architecture** — brief description of agent loop, tools, memory
5. **Example output** — reference `example_output/report.md`

### Step 8: Generate Example Output

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
