from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from privacy_enabled_agents import PII_PRELUDE_PROMPT, PrivacyEnabledAgentState
from privacy_enabled_agents.topics import AgentFactory

BASIC_AGENT_PROMPT = """
You are a helpful and professional assistant designed to assist users with various tasks. 
Your primary role is to provide accurate information, answer questions, and guide users through processes in a clear and efficient manner.
"""


class BasicAgentFactory(AgentFactory):
    @classmethod
    def create(
        cls,
        chat_model: BaseChatModel,
        checkpointer: BaseCheckpointSaver,
        runnable_config: RunnableConfig,
        prompt: str | None = None,
        pii_guarding_enabled: bool = True,
    ) -> CompiledStateGraph:
        tools: list[BaseTool] = []

        if prompt is None:
            prompt = BASIC_AGENT_PROMPT

        if pii_guarding_enabled:
            prompt = PII_PRELUDE_PROMPT + "\n" + prompt

        chat_model_with_tools = chat_model.bind_tools(
            tools,
            parallel_tool_calls=False,
        )

        agent: CompiledStateGraph = create_react_agent(
            name="basic_agent",
            model=chat_model_with_tools,
            tools=tools,
            prompt=prompt,
            checkpointer=checkpointer,
            state_schema=PrivacyEnabledAgentState,
        ).with_config(config=runnable_config)

        return agent
