from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from privacy_enabled_agents import BASE_ENTITIES


class AgentFactory(ABC):
    @classmethod
    @abstractmethod
    def create(
        cls,
        chat_model: BaseChatModel,
        checkpointer: BaseCheckpointSaver,
        runnable_config: RunnableConfig,
        prompt: str | None = None,
    ) -> CompiledStateGraph:
        pass

    @classmethod
    def supported_entities(cls) -> set[str]:
        return BASE_ENTITIES
