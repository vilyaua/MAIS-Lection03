import logging

import streamlit as st

from agent import agent
from config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("research_agent")

settings = Settings()

st.set_page_config(page_title="Research Agent", page_icon="🔍")
st.title("Research Agent")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.session_tokens = {"input": 0, "output": 0, "total": 0}

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask a research question..."):
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
                        logger.info(
                            "Tokens — input: %d, output: %d, total: %d",
                            u.get("input_tokens", 0),
                            u.get("output_tokens", 0),
                            u.get("total_tokens", 0),
                        )

            if "tools" in chunk and "messages" in chunk["tools"]:
                for msg in chunk["tools"]["messages"]:
                    status.write(f"**{msg.name}** called")
                    logger.info("Tool [%s]: %s", msg.name, msg.content[:200])

        status.update(label="Research complete", state="complete", expanded=False)
        st.markdown(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})

with st.sidebar:
    st.caption("Session token usage")
    t = st.session_state.get("session_tokens", {"input": 0, "output": 0, "total": 0})
    st.metric("Input tokens", t["input"])
    st.metric("Output tokens", t["output"])
    st.metric("Total tokens", t["total"])
