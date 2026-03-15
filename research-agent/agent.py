from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from config import SYSTEM_PROMPT, Settings
from tools import read_url, web_search, write_report

settings = Settings()


def _build_llm():
    if settings.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.model_name,
            api_key=settings.api_key.get_secret_value(),
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.api_key.get_secret_value(),
    )


llm = _build_llm()

tools = [web_search, read_url, write_report]

memory = MemorySaver()

agent = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    prompt=SYSTEM_PROMPT,
)
