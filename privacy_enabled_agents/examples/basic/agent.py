from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from privacy_enabled_agents import PII_PRELUDE_PROMPT, PrivacyEnabledAgentState

basic_agent_prompt: str = """
You are a helpful and professional assistant designed to assist users with various tasks. 
Your primary role is to provide accurate information, answer questions, and guide users through processes in a clear and efficient manner.
"""


def create_basic_agent(
    chat_model: BaseChatModel,
    checkpointer: BaseCheckpointSaver,
    runnable_config: RunnableConfig,
    prompt: str | None = None,
) -> CompiledStateGraph:
    tools: list[BaseTool] = []

    if prompt is None:
        prompt = basic_agent_prompt

    prompt = PII_PRELUDE_PROMPT + prompt

    agent: CompiledStateGraph = create_react_agent(
        name="basic_agent",
        model=chat_model,
        tools=tools,
        prompt=prompt,
        checkpointer=checkpointer,
        state_schema=PrivacyEnabledAgentState,
    ).with_config(config=runnable_config)

    return agent
