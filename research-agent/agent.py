"""Agent assembly — wires together the LLM, tools, memory, and system prompt.

This module is imported by both main.py (CLI) and app.py (FastAPI), so everything
is constructed at module level and shared as singletons.
"""

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from config import SYSTEM_PROMPT, Settings
from tools import list_reports, read_file, read_url, web_search, write_report

settings = Settings()

llm = ChatOpenAI(
    model=settings.model_name,
    api_key=settings.api_key.get_secret_value(),  # SecretStr -> plain str for the SDK
)

tools = [web_search, read_url, write_report, list_reports, read_file]

# MemorySaver keeps conversation history in-process (RAM).
# Enables multi-turn follow-up questions within a single session.
memory = MemorySaver()

# create_react_agent builds a LangGraph graph implementing the ReAct loop:
#   Reason (LLM decides what to do) -> Act (call a tool) -> Observe (feed result back) -> repeat
agent = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    prompt=SYSTEM_PROMPT,
)
