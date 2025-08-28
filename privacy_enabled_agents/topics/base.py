from abc import ABC, abstractmethod
from typing import Any, TypedDict

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


class EvalTask(TypedDict):
    instruction: str
    additional_kwargs: dict[str, Any]


class EvalTaskCreator(ABC):
    @classmethod
    @abstractmethod
    def create_eval_task(cls) -> EvalTask:
        pass
