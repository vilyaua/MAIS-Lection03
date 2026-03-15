import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import streamlit as st

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

st.set_page_config(page_title="Research Agent", page_icon="🔍")
st.title("Research Agent")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.session_tokens = {"input": 0, "output": 0, "total": 0}

# Sidebar: app info + live token metrics
with st.sidebar:
    st.caption(f"v{APP_VERSION}")
    st.markdown(f"**Provider:** `{settings.provider}`  \n**Model:** `{settings.model_name}`")
    st.divider()
    st.caption("Session token usage")
    t = st.session_state.session_tokens
    input_metric = st.empty()
    output_metric = st.empty()
    total_metric = st.empty()
    input_metric.metric("Input tokens", t["input"])
    output_metric.metric("Output tokens", t["output"])
    total_metric.metric("Total tokens", t["total"])

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


def _format_tool_status(msg) -> str:
    name = msg.name
    content = msg.content
    if name == "web_search":
        count = content.count("Title:")
        return f"🔍 **web_search** — {count} results found"
    if name == "read_url":
        if content.startswith("Error"):
            return f"🌐 **read_url** — {content[:80]}"
        return f"📄 **read_url** — extracted {len(content):,} chars"
    if name == "write_report":
        return f"💾 **write_report** — {content}"
    return f"🔧 **{name}** called"


if prompt := st.chat_input("Ask a research question..."):
    logger.info("User: %s", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    config = {
        "configurable": {"thread_id": "streamlit-session"},
        "recursion_limit": settings.max_iterations,
    }

    with st.chat_message("assistant"):
        status = st.status("Researching...", expanded=True)
        response_text = ""

        for chunk in agent.stream(
            {"messages": [("user", prompt)]},
            config=config,
        ):
            if "agent" in chunk and "messages" in chunk["agent"]:
                for msg in chunk["agent"]["messages"]:
                    if hasattr(msg, "content") and msg.content:
                        response_text = msg.content

                    if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                        u = msg.usage_metadata
                        st.session_state.session_tokens["input"] += u.get("input_tokens", 0)
                        st.session_state.session_tokens["output"] += u.get("output_tokens", 0)
                        st.session_state.session_tokens["total"] += u.get("total_tokens", 0)
                        t = st.session_state.session_tokens
                        input_metric.metric("Input tokens", t["input"])
                        output_metric.metric("Output tokens", t["output"])
                        total_metric.metric("Total tokens", t["total"])
                        logger.info(
                            "Tokens — input: %d, output: %d, total: %d",
                            u.get("input_tokens", 0),
                            u.get("output_tokens", 0),
                            u.get("total_tokens", 0),
                        )

            if "tools" in chunk and "messages" in chunk["tools"]:
                for msg in chunk["tools"]["messages"]:
                    tool_info = _format_tool_status(msg)
                    status.write(tool_info)
                    logger.info("Tool [%s]: %s", msg.name, msg.content[:300])

        status.update(label="Research complete", state="complete", expanded=False)
        st.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})
