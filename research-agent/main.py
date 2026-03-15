"""Console REPL interface for the Research Agent.

Run with: python main.py
The agent streams responses chunk-by-chunk via LangGraph's .stream() method.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from agent import agent
from config import APP_VERSION, Settings

Path("logs").mkdir(exist_ok=True)

# Dual logging: console + rotating file (5 MB, 3 backups)
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


def _format_tool_status(msg) -> str:
    """Convert a tool result message into a human-friendly one-liner for the console."""
    name = msg.name
    content = msg.content
    if name == "web_search":
        count = content.count("Title:")
        return f"  [web_search] {count} results found"
    if name == "read_url":
        if content.startswith("Error"):
            return f"  [read_url] {content[:80]}"
        return f"  [read_url] extracted {len(content):,} chars"
    if name == "write_report":
        return f"  [write_report] {content}"
    return f"  [{name}] called"


def main():
    print(f"Research Agent v{APP_VERSION} (type 'exit' to quit)")
    print(f"Model: {settings.model_name}")
    print("-" * 40)
    logger.info("Starting Research Agent v%s [%s]", APP_VERSION, settings.model_name)

    # thread_id ties all turns to one conversation so MemorySaver can track history.
    # recursion_limit caps the number of Reason->Act->Observe cycles per query.
    config = {
        "configurable": {"thread_id": "session-1"},
        "recursion_limit": settings.max_iterations,
    }

    session_tokens = {"input": 0, "output": 0, "total": 0}

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            logger.info("User exited session")
            print("Goodbye!")
            break

        logger.info("User: %s", user_input)

        # agent.stream() yields chunks as the ReAct loop progresses.
        # Two chunk types: "agent" (LLM reasoning/response) and "tools" (tool results).
        for chunk in agent.stream(
            {"messages": [("user", user_input)]},
            config=config,
        ):
            if "agent" in chunk and "messages" in chunk["agent"]:
                for msg in chunk["agent"]["messages"]:
                    if hasattr(msg, "content") and msg.content:
                        print(f"\nAgent: {msg.content}")

                    # usage_metadata is attached by LangChain to each AIMessage
                    if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                        u = msg.usage_metadata
                        logger.info(
                            "Tokens — input: %d, output: %d, total: %d",
                            u.get("input_tokens", 0),
                            u.get("output_tokens", 0),
                            u.get("total_tokens", 0),
                        )
                        session_tokens["input"] += u.get("input_tokens", 0)
                        session_tokens["output"] += u.get("output_tokens", 0)
                        session_tokens["total"] += u.get("total_tokens", 0)

            if "tools" in chunk and "messages" in chunk["tools"]:
                for msg in chunk["tools"]["messages"]:
                    print(_format_tool_status(msg))
                    logger.info("Tool [%s]: %s", msg.name, msg.content[:300])

        logger.info(
            "Session totals — input: %d, output: %d, total: %d",
            session_tokens["input"],
            session_tokens["output"],
            session_tokens["total"],
        )


if __name__ == "__main__":
    main()
