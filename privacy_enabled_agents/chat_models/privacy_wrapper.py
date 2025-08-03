from collections.abc import Callable, Sequence
from json import dumps, loads
from typing import Any, TypedDict, cast
from uuid import UUID, uuid4

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolCall
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool
from pydantic import Field

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.detection.base import BaseDetector
from privacy_enabled_agents.replacement.base import BaseReplacer


# Local class to define the input structure for the replace function
class ReplaceInput(TypedDict):
    """Input for the replace function."""

    messages: list[BaseMessage]
    detector_outputs_by_uuid: dict[str, list[Entity]]


class PrivacyEnabledChatModel(BaseChatModel):
    """Wraps a chat model to add privacy features."""

    chat_model: BaseChatModel = Field(alias="model", description="The chat model to wrap.")
    replacer: BaseReplacer = Field(description="Replacer to use for substituting sensitive information.")
    detector: BaseDetector = Field(description="Detector to use for identifying sensitive information.")
    context_id: UUID = Field(description="The context ID for the chat model.", default_factory=uuid4)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Detect sensitive information in the messages
        detect_runnable: RunnableLambda[list[BaseMessage], tuple[list[BaseMessage], dict[str, list[Entity]]]] = RunnableLambda(
            self._detect_entities
        )
        transformed_messages: list[BaseMessage]
        detector_outputs_by_uuid: dict[str, list[Entity]]
        transformed_messages, detector_outputs_by_uuid = detect_runnable.invoke(input=messages, **kwargs)

        # Replace sensitive information with placeholders
        replace_runnable: RunnableLambda[ReplaceInput, list[BaseMessage]] = RunnableLambda(self._replace_entities)
        replaced_messages: list[BaseMessage] = replace_runnable.invoke(
            input={
                "messages": transformed_messages,
                "detector_outputs_by_uuid": detector_outputs_by_uuid,
            },
            **kwargs,
        )

        # Generate a response using the chat model
        censored_output: BaseMessage = self.chat_model.invoke(
            input=replaced_messages,
            stop=stop,
            **kwargs,
        )

        # Restore the original text in the response
        restore_runnable: RunnableLambda[BaseMessage, BaseMessage] = RunnableLambda(self._restore_entities)
        restored_output: BaseMessage = restore_runnable.invoke(input=censored_output, **kwargs)

        # Create a ChatGeneration object with the restored output
        generation = ChatGeneration(message=restored_output)
        return ChatResult(generations=[generation], llm_output={})

    @property
    def _llm_type(self) -> str:
        return f"privacy-enabled-{self.chat_model._llm_type}"

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
            context_id=self.context_id,
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
            messages (list[BaseMessage]): The messages to analyze.
            detection_results (list[DetectionResult]): The detection results for the messages.

        Returns:
            list[BaseMessage]: The messages with sensitive information replaced.
        """

        replaced_messages: list[BaseMessage] = []
        detector_outputs_by_uuid: dict[str, list[Entity]] = input.get("detector_outputs_by_uuid", {})
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
                    text=message.content, entities=matching_detector_output, context_id=self.context_id
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
                            context_id=self.context_id,
                        )
                        replaced_tool_call["args"] = loads(replaced_args)
                        replaced_tool_calls.append(replaced_tool_call)
                    else:
                        replaced_tool_calls.append(tool_call)

                assert isinstance(replaced_message, AIMessage), "Replaced message must be an AIMessage if message is an AIMessage"
                replaced_message.tool_calls = replaced_tool_calls

            replaced_messages.append(replaced_message)

        return replaced_messages

    def _restore_entities(self, message: BaseMessage) -> BaseMessage:
        """Restore sensitive information in the response content.

        Args:
            chat_result (ChatResult): The chat result to restore.

        Returns:
            ChatResult: The chat result with sensitive information restored.
        """
        # Create a copy of the message to avoid modifying the original
        restored_message: BaseMessage = message.model_copy()
        # Restore sensitive information in the message content
        assert isinstance(message.content, str), "Message content must be a string"
        restored_message.content = self.replacer.restore(text=message.content, context_id=self.context_id)

        # If the message is an AIMessage and has tool calls, restore them as well
        if isinstance(message, AIMessage) and len(message.tool_calls) > 0:
            restored_tool_calls: list[ToolCall] = []
            for tool_call in message.tool_calls:
                # Restore the tool call arguments
                restored_tool_call: ToolCall = tool_call.copy()
                tool_call_args: str = dumps(tool_call.get("args", {}))
                restored_args = self.replacer.restore(text=tool_call_args, context_id=self.context_id)
                restored_tool_call["args"] = loads(restored_args)
                restored_tool_calls.append(restored_tool_call)

            assert isinstance(restored_message, AIMessage), "Restored message must be an AIMessage if message is an AIMessage"
            restored_message.tool_calls = restored_tool_calls

        return restored_message
