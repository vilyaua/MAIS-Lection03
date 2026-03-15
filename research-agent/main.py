import logging

from agent import agent
from config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("research_agent")

settings = Settings()


def main():
    print("Research Agent (type 'exit' to quit)")
    print("-" * 40)

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
                    logger.info("Tool [%s]: %s", msg.name, msg.content[:200])

        logger.info(
            "Session totals — input: %d, output: %d, total: %d",
            session_tokens["input"],
            session_tokens["output"],
            session_tokens["total"],
        )


if __name__ == "__main__":
    main()
