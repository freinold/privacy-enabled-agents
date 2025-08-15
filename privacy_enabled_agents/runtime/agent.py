from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph.state import CompiledStateGraph

from privacy_enabled_agents.chat_models import PrivacyEnabledChatModel
from privacy_enabled_agents.detection import BaseDetector, RegexDetector, RemoteGlinerDetector
from privacy_enabled_agents.replacement import BaseReplacer, HashReplacer, MockEncryptionReplacer, PlaceholderReplacer, PseudonymReplacer
from privacy_enabled_agents.storage import (
    BaseConversationStorage,
    BaseEntityStorage,
    EncryptionEntityStorage,
    ValkeyConversationStorage,
    ValkeyEntityStorage,
)
from privacy_enabled_agents.topics import (
    AgentFactory,
    BasicAgentFactory,
    FinanceAgentFactory,
    MedicalAgentFactory,
    PublicServiceAgentFactory,
    WebSearchAgentFactory,
)

AgentFactoryMap: dict[Literal["basic", "websearch", "financial", "medical", "public service"], type[AgentFactory]] = {
    "basic": BasicAgentFactory,
    "financial": FinanceAgentFactory,
    "medical": MedicalAgentFactory,
    "public service": PublicServiceAgentFactory,
    "websearch": WebSearchAgentFactory,
}


def create_privacy_agent(
    topic: Literal["basic", "websearch", "financial", "medical", "public service"] = "basic",
    model_provider: Literal["openai", "mistral"] = "mistral",
    model_name: str = "mistral-medium-2508",
    detector: Literal["gliner", "regex"] = "gliner",
    replacer: Literal["placeholder", "encryption", "hash", "pseudonym"] = "placeholder",
    entity_store: Literal["valkey", "encryption"] = "valkey",
    conversation_store: Literal["valkey"] = "valkey",
    checkpointer: Literal["redis"] = "redis",
    langfuse_enabled: bool = True,
    prompt: str | None = None,
) -> tuple[CompiledStateGraph, PrivacyEnabledChatModel]:
    """Create a privacy agent.

    Args:
        topic (Literal["basic", "websearch", "financial", "medical", "public service"], optional): The topic of the agent. Defaults to "basic".
        model_provider (Literal["openai", "mistral"], optional): The model provider to use. Defaults to "mistral".
        model_name (str, optional): The name of the model to use. Defaults to "mistral-medium-2508".
        detector (Literal["gliner", "regex"], optional): The detector to use. Defaults to "gliner".
        replacer (Literal["placeholder", "encryption", "hash", "pseudonym"], optional): The replacer to use. Defaults to "placeholder".
        entity_store (Literal["valkey", "encryption"], optional): The entity store to use. Defaults to "valkey".
        conversation_store (Literal["valkey"], optional): The conversation store to use. Defaults to "valkey".
        checkpointer (Literal["redis"], optional): The checkpointer to use. Defaults to "redis".
        langfuse_enabled (bool, optional): Whether to enable LangFuse integration. Defaults to True.
        prompt (str | None, optional): The prompt override to use for the agent. Defaults to None.

    Raises:
        ValueError: If one of the parameters is unsupported.
        RuntimeError: If the agent creation fails.

    Returns:
        CompiledStateGraph: _description_
    """
    # Agent factory lookup
    agent_factory: type[AgentFactory] | None = AgentFactoryMap.get(topic)
    if agent_factory is None:
        raise ValueError(f"Unsupported agent topic: {topic}")

    supported_entities: set[str] = agent_factory.supported_entities()

    # Chat model creation
    chat_model: BaseChatModel
    match model_provider:
        case "openai":
            from langchain_openai import ChatOpenAI

            chat_model = ChatOpenAI(model=model_name)
        case "mistral":
            from langchain_mistralai import ChatMistralAI

            chat_model = ChatMistralAI(model=model_name)  # type: ignore
        case _:
            raise ValueError(f"Unsupported model provider: {model_provider}")

    # Detector creation
    detector_instance: BaseDetector
    match detector:
        case "gliner":
            detector_instance = RemoteGlinerDetector(supported_entities=supported_entities)
        case "regex":
            detector_instance = RegexDetector()
        case _:
            raise ValueError(f"Unsupported detector: {detector}")

    # Entity store creation
    entity_store_instance: BaseEntityStorage
    match entity_store:
        case "valkey":
            entity_store_instance = ValkeyEntityStorage(db=0)
        case "encryption":
            if replacer != "encryption":
                raise ValueError("Encryption entity store requires 'encryption' replacer")
            entity_store_instance = EncryptionEntityStorage()
        case _:
            raise ValueError(f"Unsupported entity store: {entity_store}")

    # Replacer creation
    replacer_instance: BaseReplacer
    match replacer:
        case "placeholder":
            replacer_instance = PlaceholderReplacer(entity_storage=entity_store_instance)
        case "encryption":
            if entity_store != "encryption":
                raise ValueError("Encryption replacer requires 'encryption' entity store")
            replacer_instance = MockEncryptionReplacer(entity_storage=entity_store_instance)
        case "hash":
            replacer_instance = HashReplacer(entity_storage=entity_store_instance)
        case "pseudonym":
            replacer_instance = PseudonymReplacer(entity_storage=entity_store_instance)
        case _:
            raise ValueError(f"Unsupported replacer: {replacer}")

    conversation_store_instance: BaseConversationStorage
    match conversation_store:
        case "valkey":
            conversation_store_instance = ValkeyConversationStorage(db=1)
        case _:
            raise ValueError(f"Unsupported conversation store: {conversation_store}")

    # Create the privacy-enabled chat model
    privacy_chat_model = PrivacyEnabledChatModel(
        model=chat_model,
        replacer=replacer_instance,
        detector=detector_instance,
        conversation_storage=conversation_store_instance,
    )

    # Checkpointer creation
    checkpointer_instance: BaseCheckpointSaver
    match checkpointer:
        case "redis":
            checkpointer_instance = RedisSaver(
                redis_url="redis://localhost:6380",
                ttl={
                    "default_ttl": 3600,
                    "refresh_on_read": True,
                },
            )
            checkpointer_instance.setup()
        case _:
            raise ValueError(f"Unsupported checkpointer: {checkpointer}")

    # Langfuse setup
    config: RunnableConfig
    if langfuse_enabled:
        from langfuse import Langfuse, get_client  # type: ignore
        from langfuse.langchain import CallbackHandler

        langfuse: Langfuse = get_client()
        if not langfuse.auth_check():
            raise RuntimeError("Langfuse authentication failed. Please check your configuration.")

        langfuse_handler = CallbackHandler()
        config = RunnableConfig(callbacks=[langfuse_handler])
    else:
        config = RunnableConfig()

    # Create the agent
    agent: CompiledStateGraph = agent_factory.create(
        chat_model=privacy_chat_model,
        checkpointer=checkpointer_instance,
        runnable_config=config,
        prompt=prompt,
    )

    return agent, privacy_chat_model
