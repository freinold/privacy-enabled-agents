from logging import Logger, getLogger
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

from .config import PrivacyAgentConfig, PrivacyAgentConfigDict

logger: Logger = getLogger(__name__)

AgentFactoryMap: dict[Literal["basic", "websearch", "finance", "medical", "public-service"], type[AgentFactory]] = {
    "basic": BasicAgentFactory,
    "finance": FinanceAgentFactory,
    "medical": MedicalAgentFactory,
    "public-service": PublicServiceAgentFactory,
    "websearch": WebSearchAgentFactory,
}


def create_privacy_agent(
    config: PrivacyAgentConfig | PrivacyAgentConfigDict = PrivacyAgentConfig(),
) -> tuple[CompiledStateGraph, PrivacyEnabledChatModel]:
    """Create a privacy agent.

    Args:
        config (PrivacyAgentConfig): The configuration for the privacy agent.

    Raises:
        ValueError: If one of the parameters is unsupported.
        RuntimeError: If the agent creation fails.

    Returns:
        CompiledStateGraph: The compiled state graph for the privacy agent.
    """
    if isinstance(config, dict):
        config = PrivacyAgentConfig.model_validate(config)

    # Agent factory lookup
    agent_factory: type[AgentFactory] | None = AgentFactoryMap.get(config.topic)
    if agent_factory is None:
        raise ValueError(f"Unsupported agent topic: {config.topic}")

    supported_entities: set[str] = agent_factory.supported_entities()

    # Chat model creation
    chat_model: BaseChatModel
    match config.model_provider:
        case "openai":
            from langchain_openai import ChatOpenAI

            chat_model = ChatOpenAI(model=config.model_name, temperature=config.model_temperature)
        case "mistral":
            from langchain_mistralai import ChatMistralAI

            chat_model = ChatMistralAI(model=config.model_name, temperature=config.model_temperature)  # type: ignore
        case _:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")

    # Detector creation
    detector_instance: BaseDetector
    match config.detector:
        case "gliner":
            detector_instance = RemoteGlinerDetector(supported_entities=supported_entities, threshold=config.detector_threshold)
        case "regex":
            detector_instance = RegexDetector()
        case _:
            raise ValueError(f"Unsupported detector: {config.detector}")

    # Entity store creation
    entity_store_instance: BaseEntityStorage
    match config.entity_store:
        case "valkey":
            entity_store_instance = ValkeyEntityStorage(db=0)
        case "encryption":
            if config.replacer != "encryption":
                raise ValueError("Encryption entity store requires 'encryption' replacer")
            entity_store_instance = EncryptionEntityStorage()
        case _:
            raise ValueError(f"Unsupported entity store: {config.entity_store}")

    # Replacer creation
    replacer_instance: BaseReplacer
    match config.replacer:
        case "placeholder":
            replacer_instance = PlaceholderReplacer(entity_storage=entity_store_instance)
        case "encryption":
            if config.entity_store != "encryption":
                raise ValueError("Encryption replacer requires 'encryption' entity store")
            replacer_instance = MockEncryptionReplacer(entity_storage=entity_store_instance)
        case "hash":
            replacer_instance = HashReplacer(entity_storage=entity_store_instance)
        case "pseudonym":
            replacer_instance = PseudonymReplacer(entity_storage=entity_store_instance)
        case _:
            raise ValueError(f"Unsupported replacer: {config.replacer}")

    conversation_store_instance: BaseConversationStorage
    match config.conversation_store:
        case "valkey":
            conversation_store_instance = ValkeyConversationStorage(db=1)
        case _:
            raise ValueError(f"Unsupported conversation store: {config.conversation_store}")

    # Create the privacy-enabled chat model
    privacy_chat_model = PrivacyEnabledChatModel(
        model=chat_model,
        replacer=replacer_instance,
        detector=detector_instance,
        conversation_storage=conversation_store_instance,
    )

    # Checkpointer creation
    checkpointer_instance: BaseCheckpointSaver
    match config.checkpointer:
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
            raise ValueError(f"Unsupported checkpointer: {config.checkpointer}")

    # Langfuse setup
    runnable_config: RunnableConfig
    system_prompt: str | None
    if config.langfuse_enabled:
        from langfuse import Langfuse, get_client  # type: ignore
        from langfuse.langchain import CallbackHandler

        langfuse: Langfuse = get_client()
        if not langfuse.auth_check():
            raise RuntimeError("Langfuse authentication failed. Please check your configuration.")

        langfuse_handler = CallbackHandler()
        runnable_config = RunnableConfig(callbacks=[langfuse_handler])

        # System prompt retrieval
        if config.system_prompt is None:
            try:
                system_prompt = langfuse.get_prompt(name=config.topic).prompt
            except Exception as e:
                logger.warning(f"Failed to get Langfuse prompt: {e}")
                system_prompt = None
        else:
            system_prompt = config.system_prompt
    else:
        system_prompt = config.system_prompt
        runnable_config = RunnableConfig()

    # Create the agent
    agent: CompiledStateGraph = agent_factory.create(
        chat_model=privacy_chat_model,
        checkpointer=checkpointer_instance,
        runnable_config=runnable_config,
        prompt=system_prompt,
        pii_guarding_enabled=True,
    )

    return agent, privacy_chat_model


def create_agent(
    config: PrivacyAgentConfig | PrivacyAgentConfigDict = PrivacyAgentConfig(),
) -> CompiledStateGraph:
    """Create a non-privacy agent using the same config and factories as the privacy agent.

    Args:
        config (PrivacyAgentConfig): The configuration for the agent.

    Raises:
        ValueError: If one of the parameters is unsupported.
        RuntimeError: If the agent creation fails.

    Returns:
        CompiledStateGraph: The compiled state graph for the agent.
    """
    if isinstance(config, dict):
        config = PrivacyAgentConfig.model_validate(config)

    # Agent factory lookup
    agent_factory: type[AgentFactory] | None = AgentFactoryMap.get(config.topic)
    if agent_factory is None:
        raise ValueError(f"Unsupported agent topic: {config.topic}")

    # Chat model creation (without privacy wrapper)
    chat_model: BaseChatModel
    match config.model_provider:
        case "openai":
            from langchain_openai import ChatOpenAI

            chat_model = ChatOpenAI(model=config.model_name, temperature=config.model_temperature)
        case "mistral":
            from langchain_mistralai import ChatMistralAI

            chat_model = ChatMistralAI(model=config.model_name, temperature=config.model_temperature)  # type: ignore
        case _:
            raise ValueError(f"Unsupported model provider: {config.model_provider}")

    # Checkpointer creation
    checkpointer_instance: BaseCheckpointSaver
    match config.checkpointer:
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
            raise ValueError(f"Unsupported checkpointer: {config.checkpointer}")

    # Langfuse setup
    runnable_config: RunnableConfig
    system_prompt: str | None
    if config.langfuse_enabled:
        from langfuse import Langfuse, get_client  # type: ignore
        from langfuse.langchain import CallbackHandler

        langfuse: Langfuse = get_client()
        if not langfuse.auth_check():
            raise RuntimeError("Langfuse authentication failed. Please check your configuration.")

        langfuse_handler = CallbackHandler()
        runnable_config = RunnableConfig(callbacks=[langfuse_handler])

        # System prompt retrieval
        if config.system_prompt is None:
            try:
                system_prompt = langfuse.get_prompt(name=config.topic).prompt
            except Exception as e:
                logger.warning(f"Failed to get Langfuse prompt: {e}")
                system_prompt = None
        else:
            system_prompt = config.system_prompt
    else:
        system_prompt = config.system_prompt
        runnable_config = RunnableConfig()

    # Create the agent (using the regular chat model instead of privacy-enabled one)
    agent: CompiledStateGraph = agent_factory.create(
        chat_model=chat_model,
        checkpointer=checkpointer_instance,
        runnable_config=runnable_config,
        prompt=system_prompt,
        pii_guarding_enabled=False,
    )

    return agent
