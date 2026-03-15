# Research Agent

An interactive AI research agent that autonomously searches the web, reads articles, and produces structured Markdown reports. Built with LangChain and LangGraph.

## Setup

### Option 1: Docker (recommended)

```bash
cp .env.example .env
# Edit .env and add your API key

docker compose up --build
# Open http://localhost:8501
```

### Option 2: Local

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your API key

# 4. Run (pick one)
streamlit run app.py      # Web UI at http://localhost:8501
python main.py            # Console REPL
```

### Environment Variables

| Variable     | Description                          | Example            |
|-------------|--------------------------------------|--------------------|
| `API_KEY`   | LLM provider API key                | `sk-...`           |
| `MODEL_NAME`| Model identifier                     | `gpt-4.1-mini`    |
| `PROVIDER`  | `openai` or `anthropic`             | `openai`           |

## Usage

### Web UI (Streamlit)

Open `http://localhost:8501` — type a question, watch the agent research in real time. Token usage is displayed in the sidebar.

### Console

```
Research Agent (type 'exit' to quit)
----------------------------------------

You: Compare three RAG approaches: naive, sentence-window, and parent-child retrieval

Agent: [researches the topic using multiple tool calls, then presents findings]
Agent: Report saved successfully to: output/rag_comparison.md

You: Now focus on the parent-child approach — what are the best practices?

Agent: [remembers previous context, does more research]

You: exit
Goodbye!
```

## Architecture

```
research-agent/
├── app.py            # Streamlit web UI
├── main.py           # Console REPL
├── agent.py          # Agent setup — LLM, tools, memory, create_react_agent
├── tools.py          # Tool implementations — web_search, read_url, write_report
├── config.py         # Settings (pydantic-settings) and system prompt
├── requirements.txt  # Pinned dependencies
├── Dockerfile        # Container image
├── docker-compose.yml
├── .env.example      # Environment variable template
├── example_output/   # Sample generated report
│   └── report.md
└── output/           # Agent-generated reports (gitignored)
```

### Agent Loop

The agent uses LangGraph's `create_react_agent` which implements the ReAct (Reason + Act) pattern:

1. **Reason** — The LLM analyzes the user's query and decides what to do
2. **Act** — The agent calls a tool (search, read, write)
3. **Observe** — The tool result is fed back into the LLM context
4. **Repeat** — Until the agent has enough information to answer

### Tools

| Tool           | Purpose                                         |
|---------------|--------------------------------------------------|
| `web_search`  | Search DuckDuckGo for relevant sources           |
| `read_url`    | Extract full text from a web page (truncated)    |
| `write_report`| Save the final Markdown report to `output/`      |

### Context Engineering

- `read_url` truncates page text to 8000 characters to prevent context window overflow
- `web_search` returns only titles, URLs, and snippets (not full pages)
- `max_iterations` (default: 25) prevents the agent from looping indefinitely

### Memory

Uses `MemorySaver` checkpointer — the agent remembers all messages within a session, enabling follow-up questions and multi-turn conversations.
