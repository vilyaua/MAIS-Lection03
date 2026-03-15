"""FastAPI web interface with Server-Sent Events (SSE) streaming.

Run with: uvicorn app:app --reload
Endpoints:
  GET /           — chat UI (single-page HTML)
  GET /api/info   — version + model metadata
  GET /api/chat?q — SSE stream of agent responses
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from agent import agent
from config import APP_VERSION, Settings

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler("logs/agent.log", maxBytes=5_000_000, backupCount=3),
    ],
)
logger = logging.getLogger("research_agent")

settings = Settings()
app = FastAPI(title="Research Agent", version=APP_VERSION)

session_tokens = {"input": 0, "output": 0, "total": 0}


def _get_tool_call_args(name: str, args: dict) -> str:
    """Extract the primary argument from a tool call for display."""
    if name == "web_search":
        return args.get("query", "")
    if name == "read_url":
        return args.get("url", "")
    if name == "write_report":
        return args.get("description", "")
    return ""


def _format_tool_event(msg, call_args: str = "") -> dict:
    """Convert a tool result into a compact dict for the SSE stream."""
    name = msg.name
    content = msg.content
    if name == "web_search":
        count = content.count("Title:")
        return {"tool": name, "args": call_args, "detail": f"{count} results found"}
    if name == "read_url":
        if content.startswith("Error"):
            return {"tool": name, "args": call_args, "detail": content[:80]}
        return {"tool": name, "args": call_args, "detail": f"extracted {len(content):,} chars"}
    if name == "write_report":
        return {"tool": name, "args": call_args, "detail": content}
    return {"tool": name, "args": call_args, "detail": "called"}


def _sync_stream(prompt: str, config: dict):
    """Run agent.stream in a sync context (called from a thread via run_in_executor)."""
    yield from agent.stream(
        {"messages": [("user", prompt)]},
        config=config,
    )


async def _stream_response(prompt: str) -> AsyncGenerator[str, None]:
    """Bridge sync LangGraph streaming into async SSE.

    LangGraph's agent.stream() is synchronous and blocks the calling thread.
    To avoid blocking FastAPI's event loop, we run it in a thread pool and
    shuttle chunks through an asyncio.Queue back to the SSE generator.
    """
    config = {
        "configurable": {"thread_id": "web-session"},
        "recursion_limit": settings.max_iterations,
    }

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    async def _produce():
        def _run():
            for chunk in _sync_stream(prompt, config):
                loop.call_soon_threadsafe(queue.put_nowait, chunk)
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel: stream finished

        await loop.run_in_executor(None, _run)

    task = asyncio.create_task(_produce())

    # Buffer tool call args (from "agent" chunks) so we can pair them
    # with tool results (from "tools" chunks) — they arrive in separate chunks.
    pending_calls: dict[str, str] = {}  # tool_call_id -> display arg string

    # Consume chunks from the queue and yield SSE events
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        if "agent" in chunk and "messages" in chunk["agent"]:
            for msg in chunk["agent"]["messages"]:
                if hasattr(msg, "content") and msg.content:
                    yield f"data: {json.dumps({'type': 'message', 'content': msg.content})}\n\n"

                # Capture tool call arguments for later pairing with results
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        pending_calls[tc["id"]] = _get_tool_call_args(tc["name"], tc["args"])

                if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    u = msg.usage_metadata
                    session_tokens["input"] += u.get("input_tokens", 0)
                    session_tokens["output"] += u.get("output_tokens", 0)
                    session_tokens["total"] += u.get("total_tokens", 0)
                    yield f"data: {json.dumps({'type': 'tokens', 'data': session_tokens})}\n\n"
                    logger.info(
                        "Tokens — input: %d, output: %d, total: %d",
                        u.get("input_tokens", 0),
                        u.get("output_tokens", 0),
                        u.get("total_tokens", 0),
                    )

        if "tools" in chunk and "messages" in chunk["tools"]:
            for msg in chunk["tools"]["messages"]:
                call_args = pending_calls.pop(getattr(msg, "tool_call_id", ""), "")
                event = _format_tool_event(msg, call_args)
                yield f"data: {json.dumps({'type': 'tool', **event})}\n\n"
                logger.info("Tool [%s]: %s", msg.name, msg.content[:300])

    await task
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@app.get("/", response_class=HTMLResponse)
async def index():
    return CHAT_HTML


@app.get("/api/info")
async def info():
    return {
        "version": APP_VERSION,
        "model": settings.model_name,
        "tokens": session_tokens,
    }


@app.get("/api/chat")
async def chat(q: str):
    logger.info("User: %s", q)
    return StreamingResponse(
        _stream_response(q),
        media_type="text/event-stream",
    )


CHAT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Research Agent</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #f7f7f8; color: #1a1a1a; display: flex; height: 100vh; }
  .sidebar { width: 240px; background: #1e1e2e; color: #cdd6f4; padding: 20px;
             display: flex; flex-direction: column; gap: 16px; }
  .sidebar h2 { font-size: 16px; color: #89b4fa; }
  .sidebar .meta { font-size: 12px; color: #6c7086; }
  .sidebar .metric { background: #313244; border-radius: 8px; padding: 10px; }
  .sidebar .metric .label { font-size: 11px; color: #6c7086; text-transform: uppercase; }
  .sidebar .metric .value { font-size: 20px; font-weight: 600; color: #cdd6f4; }
  .main { flex: 1; display: flex; flex-direction: column; }
  .messages { flex: 1; overflow-y: auto; padding: 20px; display: flex;
              flex-direction: column; gap: 12px; }
  .msg { max-width: 80%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; }
  .msg.user { align-self: flex-end; background: #2563eb; color: white; }
  .msg.assistant { align-self: flex-start; background: white; border: 1px solid #e5e7eb; }
  .msg.assistant pre { background: #f3f4f6; padding: 8px; border-radius: 6px;
                       overflow-x: auto; font-size: 13px; margin: 8px 0; }
  .msg.assistant code { font-size: 13px; }
  .tool-log { font-size: 12px; color: #6b7280; padding: 4px 16px; }
  .input-bar { padding: 16px 20px; background: white; border-top: 1px solid #e5e7eb;
               display: flex; gap: 8px; }
  .input-bar input { flex: 1; padding: 10px 14px; border: 1px solid #d1d5db;
                     border-radius: 8px; font-size: 14px; outline: none; }
  .input-bar input:focus { border-color: #2563eb; }
  .input-bar button { padding: 10px 20px; background: #2563eb; color: white;
                      border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
  .input-bar button:disabled { background: #93c5fd; cursor: not-allowed; }
</style>
</head>
<body>
<div class="sidebar">
  <h2>Research Agent</h2>
  <div class="meta" id="meta">Loading...</div>
  <div class="metric"><div class="label">Input tokens</div><div class="value" id="t-in">0</div></div>
  <div class="metric"><div class="label">Output tokens</div><div class="value" id="t-out">0</div></div>
  <div class="metric"><div class="label">Total tokens</div><div class="value" id="t-total">0</div></div>
</div>
<div class="main">
  <div class="messages" id="messages"></div>
  <div class="input-bar">
    <input type="text" id="input" placeholder="Ask a research question..." autofocus />
    <button id="send" onclick="send()">Send</button>
  </div>
</div>
<script>
  const msgs = document.getElementById('messages');
  const input = document.getElementById('input');
  const btn = document.getElementById('send');

  fetch('/api/info').then(r=>r.json()).then(d=>{
    document.getElementById('meta').innerHTML =
      `v${d.version}<br><b>Model:</b> ${d.model}`;
    updateTokens(d.tokens);
  });

  input.addEventListener('keydown', e => { if(e.key==='Enter' && !btn.disabled) send(); });

  function addMsg(role, html) {
    const d = document.createElement('div');
    d.className = 'msg ' + role;
    d.innerHTML = html;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }

  function addTool(text) {
    const d = document.createElement('div');
    d.className = 'tool-log';
    d.textContent = text;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function updateTokens(t) {
    document.getElementById('t-in').textContent = t.input.toLocaleString();
    document.getElementById('t-out').textContent = t.output.toLocaleString();
    document.getElementById('t-total').textContent = t.total.toLocaleString();
  }

  function formatMd(text) {
    return text
      .replace(/```(\\w*)\\n([\\s\\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
      .replace(/\\*(.+?)\\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/^### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^## (.+)$/gm, '<h3>$1</h3>')
      .replace(/^# (.+)$/gm, '<h2>$1</h2>')
      .replace(/^- (.+)$/gm, '&bull; $1<br>')
      .replace(/\\n/g, '<br>');
  }

  async function send() {
    const q = input.value.trim();
    if (!q) return;
    input.value = '';
    btn.disabled = true;
    addMsg('user', q);
    const el = addMsg('assistant', '<em>Researching...</em>');

    const es = new EventSource('/api/chat?q=' + encodeURIComponent(q));
    let lastContent = '';

    es.onmessage = e => {
      const d = JSON.parse(e.data);
      if (d.type === 'message') { lastContent = d.content; el.innerHTML = formatMd(d.content); }
      if (d.type === 'tokens') updateTokens(d.data);
      if (d.type === 'tool') addTool(`\\u2192 ${d.tool}${d.args ? '("'+d.args+'")' : ''} \\u2014 ${d.detail}`);
      if (d.type === 'done') { es.close(); btn.disabled = false; input.focus(); }
      msgs.scrollTop = msgs.scrollHeight;
    };
    es.onerror = () => { es.close(); btn.disabled = false; };
  }
</script>
</body>
</html>
"""
