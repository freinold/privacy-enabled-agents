import logging
from collections.abc import Callable, Sequence
from hashlib import md5
from json import dumps, loads
from typing import Any, TypedDict, cast, override
from uuid import UUID, uuid4

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolCall
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool
from pydantic import Field

from privacy_enabled_agents import Entity
from privacy_enabled_agents.detection import BaseDetector
from privacy_enabled_agents.replacement import BaseReplacer
from privacy_enabled_agents.storage import BaseConversationStorage

# Create logger for this module
logger = logging.getLogger(__name__)


# Local class to define the input structure for the replace function
class ReplaceInput(TypedDict):
    """Input for the replace function."""

    messages: list[BaseMessage]
    detector_outputs_by_uuid: dict[str, list[Entity]]
    thread_id: UUID


class PrivacyEnabledChatModel(BaseChatModel):
    """Wraps a chat model to add privacy features."""

    chat_model: BaseChatModel = Field(alias="model", description="The chat model to wrap.")
    replacer: BaseReplacer = Field(description="Replacer to use for substituting sensitive information.")
    detector: BaseDetector = Field(description="Detector to use for identifying sensitive information.")
    conversation_storage: BaseConversationStorage | None = Field(
        default=None, description="Storage for privacy-protected conversation messages."
    )

    def _get_thread_id(self, **kwargs: Any) -> str | None:
        """Extract thread_id from kwargs."""
        logger.debug(f"_get_thread_id called with kwargs keys: {list(kwargs.keys())}")

        # Check if thread_id was passed directly as a kwarg
        thread_id: str | None = kwargs.get("thread_id")
        logger.debug(f"extracted thread_id from kwargs: {thread_id}")

        return thread_id

    def _string_to_uuid(self, string: str | None) -> UUID | None:
        """Extract thread_id from kwargs config and convert to UUID."""
        if string is None:
            return None

        try:
            return UUID(string)
        except ValueError:
            # If string is not a valid UUID, generate one from it
            return UUID(md5(string.encode()).hexdigest())

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Extract thread_id from kwargs config
        thread_id: str | None = self._get_thread_id(**kwargs)
        thread_id_uuid: UUID | None = self._string_to_uuid(thread_id)

        if thread_id_uuid is None:
            logger.debug("No thread_id provided, doing one-time detection and replacement")
            thread_id_uuid = uuid4()

        if thread_id is None:
            thread_id = str(thread_id_uuid)  # Use the UUID as the thread_id if not provided

        # Filter out thread_id from kwargs for lambda functions
        filtered_kwargs: dict[str, Any] = {k: v for k, v in kwargs.items() if k != "thread_id"}

        # Get existing privacy-protected messages from storage
        existing_protected_messages: list[BaseMessage] = []
        if self.conversation_storage and thread_id_uuid:
            existing_protected_messages = self.conversation_storage.get_encrypted_messages(thread_id=thread_id_uuid)
            logger.debug(f"Retrieved {len(existing_protected_messages)} existing protected messages")

        # Determine which messages are new (not in storage)
        # Since messages always contain the complete history, new messages are at the end
        new_messages: list[BaseMessage] = []
        num_protected_messages: int = len(existing_protected_messages)
        if num_protected_messages < len(messages):
            # New messages are at the end of the list
            new_messages = messages[num_protected_messages:]
            logger.debug(f"Identified {len(new_messages)} new messages to process")
        else:
            # If storage has same or more messages, no new messages to process
            logger.debug("No new messages to process")

        # Only process new messages for detection and replacement
        new_transformed_messages: list[BaseMessage] = []
        new_replaced_messages: list[BaseMessage] = []

        if len(new_messages) > 0:
            # Detect sensitive information in new messages only
            detect_runnable: RunnableLambda[list[BaseMessage], tuple[list[BaseMessage], dict[str, list[Entity]]]] = RunnableLambda(
                self._detect_entities
            )
            detector_outputs_by_uuid: dict[str, list[Entity]]
            new_transformed_messages, detector_outputs_by_uuid = detect_runnable.invoke(input=new_messages, **filtered_kwargs)

            # Replace sensitive information with placeholders in new messages only
            replace_runnable: RunnableLambda[ReplaceInput, list[BaseMessage]] = RunnableLambda(self._replace_entities)
            new_replaced_messages = replace_runnable.invoke(
                input={
                    "messages": new_transformed_messages,
                    "detector_outputs_by_uuid": detector_outputs_by_uuid,
                    "thread_id": thread_id_uuid,
                },
                **filtered_kwargs,
            )

        # Combine existing protected messages with newly processed messages
        all_replaced_messages: list[BaseMessage] = existing_protected_messages + new_replaced_messages

        # Generate a response using the chat model
        censored_output: BaseMessage = self.chat_model.invoke(
            input=all_replaced_messages,
            stop=stop,
            **filtered_kwargs,
        )

        # Store privacy-protected messages in conversation storage if available
        if self.conversation_storage and thread_id and thread_id_uuid and new_replaced_messages:
            # Only store the new messages and the LLM response
            new_privacy_protected_messages: list[BaseMessage] = new_replaced_messages + [censored_output]
            logger.info(f"Storing {len(new_privacy_protected_messages)} new messages for thread_id {thread_id_uuid}")
            self.conversation_storage.store_encrypted_messages(thread_id=thread_id_uuid, messages=new_privacy_protected_messages)
            logger.debug("Successfully stored new messages")
        elif not new_replaced_messages:
            logger.debug("No new messages to store")
        else:
            logger.debug(
                f"Not storing messages - conversation_storage: {self.conversation_storage is not None}, thread_id: {thread_id}, thread_id_uuid: {thread_id_uuid}"
            )

        # Restore the original text in the response
        restore_runnable: RunnableLambda[BaseMessage, BaseMessage] = RunnableLambda(lambda msg: self._restore_entities(msg, thread_id_uuid))
        restored_output: BaseMessage = restore_runnable.invoke(input=censored_output, **filtered_kwargs)

        # Create a ChatGeneration object with the restored output
        generation = ChatGeneration(message=restored_output)
        return ChatResult(generations=[generation], llm_output={})

    def get_encrypted_messages(self, thread_id: str | None = None, limit: int | None = None) -> list[BaseMessage]:
        """Retrieve encrypted messages from conversation storage.

        Args:
            thread_id: Optional thread ID - if not provided, no messages will be returned
            limit: Maximum number of recent messages to retrieve

        Returns:
            List of encrypted messages with placeholders
        """
        logger.debug(f"get_encrypted_messages called with thread_id: {thread_id}")

        if not self.conversation_storage or not thread_id:
            logger.debug(f"Early return - conversation_storage: {self.conversation_storage is not None}, thread_id: {thread_id}")
            return []

        # Convert thread_id to UUID
        try:
            thread_id_uuid = UUID(thread_id)
        except ValueError:
            # If thread_id is not a valid UUID, generate one from it
            import hashlib

            thread_id_uuid = UUID(hashlib.md5(thread_id.encode()).hexdigest())

        logger.debug(f"Converted thread_id to UUID: {thread_id_uuid}")

        messages = self.conversation_storage.get_encrypted_messages(thread_id=thread_id_uuid, limit=limit)
        logger.debug(f"Retrieved {len(messages)} messages from storage")

        return messages

    def clear_conversation(self, thread_id: str | None = None) -> None:
        """Clear all encrypted messages for the specified thread.

        Args:
            thread_id: Thread ID to clear messages for
        """
        if not self.conversation_storage or not thread_id:
            return

        # Convert thread_id to UUID
        try:
            thread_id_uuid = UUID(thread_id)
        except ValueError:
            # If thread_id is not a valid UUID, generate one from it
            import hashlib

            thread_id_uuid = UUID(hashlib.md5(thread_id.encode()).hexdigest())

        self.conversation_storage.clear_conversation(thread_id=thread_id_uuid)

    @property
    def _llm_type(self) -> str:
        return f"privacy-enabled-{self.chat_model._llm_type}"

    @override
    def invoke(
        self,
        input: Any,
        config: RunnableConfig | None = None,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> BaseMessage:
        """Override invoke to extract thread_id from config and pass it as a kwarg."""
        logger.debug(f"invoke called with config: {config}")

        # Extract thread_id from config and add it to kwargs
        if config and isinstance(config, dict):
            configurable = config.get("configurable", {})
            thread_id = configurable.get("thread_id")
            if thread_id:
                kwargs["thread_id"] = thread_id
                logger.debug(f"Extracted thread_id: {thread_id} and added to kwargs")

        # Call parent invoke - the thread_id will now be passed through in kwargs
        return super().invoke(input=input, config=config, stop=stop, **kwargs)

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return dict(self.chat_model._identifying_params)

    def bind_tools(
        self, tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool], *, tool_choice: str | None = None, **kwargs: Any
    ) -> Runnable[PromptValue | str | Sequence[BaseMessage | list[str] | tuple[str, str] | str | dict[str, Any]], BaseMessage]:
        self.chat_model = cast("BaseChatModel", self.chat_model.bind_tools(tools, tool_choice=tool_choice, **kwargs))
        return self

    def _detect_entities(self, messages: list[BaseMessage]) -> tuple[list[BaseMessage], dict[str, list[Entity]]]:
        """Detect sensitive information in the messages.

        Args:
            messages (list[BaseMessage]): The messages to analyze.
            thread_id (UUID | None): The thread ID for the conversation.

        Returns:
            dict[str, DetectorOutput]: A dictionary mapping message and tool call ids to their respective detection results.
        """
        # Transform messages into a format suitable for the detector
        transformed_texts: dict[str, str] = {}
        transformed_messages: list[BaseMessage] = []
        for message in messages:
            # Copy the message to avoid modifying the original
            transformed_message = message.model_copy()
            if transformed_message.id is None:
                # Generate a new UUID for the message if it doesn't have one
                transformed_message.id = str(uuid4())

            transformed_messages.append(transformed_message)

            # Skip system messages so we don't false positive on them
            if isinstance(message, SystemMessage):
                continue

            assert isinstance(transformed_message.content, str), "Message content must be a string"

            # Add the message ID and content to the transformed texts
            transformed_texts[transformed_message.id] = transformed_message.content

            # If the message is not an AIMessage or has no tool calls, skip it
            if not isinstance(transformed_message, AIMessage) or len(transformed_message.tool_calls) == 0:
                continue

            # Iterate over tool calls and their respective arguments
            for tool_call in transformed_message.tool_calls:
                # Check if the tool call has an ID cause we need to keep track of it
                tool_call_id = tool_call.get("id")
                if tool_call_id is None:
                    raise ValueError(f"Tool call ID is missing for tool call {tool_call}")
                # Append the tool call ID and arguments dumped as a json string
                tool_call_args = dumps(tool_call.get("args", {}))
                transformed_texts[tool_call_id] = tool_call_args

        # Invoke the detector to analyze the transformed texts
        detection_results: list[list[Entity]] = self.detector.batch(
            inputs=[text for _, text in transformed_texts.items()],
        )

        # Create a mapping of message IDs to their detection results
        detector_outputs_by_uuid: dict[str, list[Entity]] = {
            msg_id: result for msg_id, result in zip(transformed_texts.keys(), detection_results)
        }

        # Filter out empty detection results
        detector_outputs_by_uuid = {msg_id: result for msg_id, result in detector_outputs_by_uuid.items() if len(result) > 0}

        # Return the filtered detection results
        return transformed_messages, detector_outputs_by_uuid

    def _replace_entities(self, input: ReplaceInput) -> list[BaseMessage]:
        """Replace sensitive information in the messages with placeholders.

        Args:
            input (ReplaceInput): Input containing messages, detection results and thread_id of the conversation.

        Returns:
            list[BaseMessage]: The messages with sensitive information replaced.
        """

        replaced_messages: list[BaseMessage] = []
        detector_outputs_by_uuid: dict[str, list[Entity]] = input.get("detector_outputs_by_uuid", {})
        thread_id: UUID = input.get("thread_id")
        for message in input.get("messages", []):
            # Copy the message to avoid modifying the original
            replaced_message: BaseMessage = message.model_copy()
            # Get the message ID cause we need it to get the detections
            message_id: str | None = message.id
            if message_id is None:
                raise ValueError(f"Message ID is missing for message {message}")

            # Replace sensitive information in the message content itself
            if matching_detector_output := detector_outputs_by_uuid.get(message_id):
                assert isinstance(message.content, str), "Message content must be a string"
                replaced_message.content = self.replacer.replace(
                    text=message.content, entities=matching_detector_output, thread_id=thread_id
                )

            # Replace sensitive information in tool calls
            if isinstance(message, AIMessage) and len(message.tool_calls) > 0:
                replaced_tool_calls: list[ToolCall] = []
                for tool_call in message.tool_calls:
                    # Get the tool call ID cause we need it to get the detections
                    tool_call_id: str | None = tool_call.get("id")
                    if tool_call_id is None:
                        raise ValueError(f"Tool call ID is missing for tool call {tool_call}")

                    # Find the matching detection output for the tool call
                    if matching_tool_call_output := detector_outputs_by_uuid.get(tool_call_id):
                        replaced_tool_call: ToolCall = tool_call.copy()
                        # Replace sensitive information in the tool call arguments
                        tool_call_args: str = dumps(tool_call.get("args", {}))
                        replaced_args = self.replacer.replace(
                            text=tool_call_args,
                            entities=matching_tool_call_output,
                            thread_id=thread_id,
                        )
                        replaced_tool_call["args"] = loads(replaced_args)
                        replaced_tool_calls.append(replaced_tool_call)
                    else:
                        replaced_tool_calls.append(tool_call)

                assert isinstance(replaced_message, AIMessage), "Replaced message must be an AIMessage if message is an AIMessage"
                replaced_message.tool_calls = replaced_tool_calls

            replaced_messages.append(replaced_message)

        return replaced_messages

    def _restore_entities(self, message: BaseMessage, thread_id: UUID) -> BaseMessage:
        """Restore sensitive information in the response content.

        Args:
            message (BaseMessage): The message to restore.
            thread_id (UUID | None): The thread ID for the conversation.

        Returns:
            BaseMessage: The message with sensitive information restored.
        """
        # Create a copy of the message to avoid modifying the original
        restored_message: BaseMessage = message.model_copy()
        # Restore sensitive information in the message content
        assert isinstance(message.content, str), "Message content must be a string"

        restored_message.content = self.replacer.restore(text=message.content, thread_id=thread_id)

        # If the message is an AIMessage and has tool calls, restore them as well
        if isinstance(message, AIMessage) and len(message.tool_calls) > 0:
            restored_tool_calls: list[ToolCall] = []
            for tool_call in message.tool_calls:
                # Restore the tool call arguments
                restored_tool_call: ToolCall = tool_call.copy()
                tool_call_args: str = dumps(tool_call.get("args", {}))
                restored_args = self.replacer.restore(text=tool_call_args, thread_id=thread_id)
                restored_tool_call["args"] = loads(restored_args)
                restored_tool_calls.append(restored_tool_call)

            assert isinstance(restored_message, AIMessage), "Restored message must be an AIMessage if message is an AIMessage"
            restored_message.tool_calls = restored_tool_calls

        return restored_message
