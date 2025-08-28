from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from privacy_enabled_agents import PrivacyEnabledAgentState
from privacy_enabled_agents.base import PII_PRELUDE_PROMPT
from privacy_enabled_agents.topics import AgentFactory

from .tools import SearchWebTool

WEBSEARCH_AGENT_PROMPT: str = """
<Role>
You are a helpful and professional web search assistant.
</Role>

<Task>
Your primary role is to assist users in finding information online efficiently and accurately.
You should always be polite, patient, and thorough in your responses, providing clear explanations and guidance.
</Task>

<Tools>
You have one tool available.

<Tool 1>
Tool Name: search_web
Description: Perform a web search with the given query via Google
Arguments:
- query: The search query string
</Tool 1>
</Tools>
"""


class WebSearchAgentFactory(AgentFactory):
    @classmethod
    def create(
        cls,
        chat_model: BaseChatModel,
        checkpointer: BaseCheckpointSaver,
        runnable_config: RunnableConfig,
        prompt: str | None = None,
        pii_guarding_enabled: bool = True,
    ) -> CompiledStateGraph:
        tools: list[BaseTool] = [
            SearchWebTool(),
        ]

        if prompt is None:
            prompt = WEBSEARCH_AGENT_PROMPT

        if pii_guarding_enabled:
            prompt = PII_PRELUDE_PROMPT + "\n" + prompt

        chat_model_with_tools = chat_model.bind_tools(
            tools,
            parallel_tool_calls=False,
        )

        agent: CompiledStateGraph = create_react_agent(
            name="websearch_agent",
            model=chat_model_with_tools,
            tools=tools,
            prompt=prompt,
            checkpointer=checkpointer,
            state_schema=PrivacyEnabledAgentState,
        ).with_config(config=runnable_config)

        return agent
