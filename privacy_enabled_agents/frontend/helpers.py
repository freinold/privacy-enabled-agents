from collections.abc import Callable, Generator
from json import dumps
from logging import Logger
from typing import Any, Literal
from uuid import uuid4

import gradio as gr
from gradio.components.chatbot import MetadataDict
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from privacy_enabled_agents.chat_models import PrivacyEnabledChatModel

message_type_map: dict[str, Literal["user", "assistant", "system"]] = {
    "human": "user",
    "ai": "assistant",
    "system": "system",
    "tool": "assistant",  # Tools are treated as assistant messages
}


def convert_lc2gr_messages(lc_messages: list[BaseMessage]) -> list[gr.ChatMessage]:
    """Convert a list of BaseMessage to Gradio ChatMessage."""
    gr_messages: list[gr.ChatMessage] = []
    for message in lc_messages:
        match message.type:
            case "human":
                gr_messages.append(gr.ChatMessage(role="user", content=message.content))
            case "ai":
                assert isinstance(message, AIMessage)
                gr_message = gr.ChatMessage(role="assistant", content=message.content)
                # # Special handler for mistral :(
                # if isinstance(message.content, list):
                #     message_content = ""
                #     for item in message.content:
                #         if isinstance(item, str):
                #             message_content += item
                #         elif isinstance(item, dict):
                #             if "text" in item:
                #                 message_content += item["text"]
                #             elif "reference_ids" in item and isinstance(item["reference_ids"], list):
                #                 reference_ids = "".join(item["reference_ids"])
                #                 message_content += reference_ids
                #     gr_message.content = message_content
                if len(message.tool_calls) > 0:
                    # We disabled parallel tool calls, so no need for iteration
                    gr_message.metadata = MetadataDict(
                        title=message.tool_calls[0]["name"],
                        log=dumps(message.tool_calls[0]["args"]),
                    )
                gr_messages.append(gr_message)
            case _:
                pass

    return gr_messages


def create_chat_function(
    topic: str,
    agent: CompiledStateGraph,
    chat_model: PrivacyEnabledChatModel,
    logger: Logger | None = None,
) -> Callable[
    [str, list[gr.ChatMessage], dict],
    Generator[tuple[list[gr.ChatMessage], list, dict] | tuple[list[gr.ChatMessage], list[gr.ChatMessage], dict[str, Any]], Any, None],
]:
    if logger is None:
        logger = Logger(f"{topic}-agent-runtime")

    def chat_fn(message: str, history: list[gr.ChatMessage], browser_state: dict):
        # Use topic-prefixed thread_id key
        thread_id_key = f"thread_id_{topic}"
        thread_id: str | None = browser_state.get(thread_id_key)
        if not thread_id:
            # Create a new thread_id for this topic if not present
            thread_id = str(uuid4())
            browser_state[thread_id_key] = thread_id

        logger.info(f"Chat function called with topic '{topic}' and thread_id: {thread_id}")

        # Add the user message to history immediately for the left chat
        user_message = gr.ChatMessage(role="user", content=message)
        updated_history = history + [user_message]

        # Yield the user message immediately
        yield updated_history, [], browser_state

        input: dict[str, Any] = {"messages": [HumanMessage(content=message)]}
        response: dict[str, Any] = agent.invoke(
            input,
            config={
                "configurable": {"thread_id": thread_id},
                "metadata": {
                    "langfuse_session_id": thread_id,
                    "langfuse_tags": [topic],
                },
            },
        )

        logger.debug(f"Agent response contains {len(response['messages'])} messages")

        # Extract all messages for the user-facing chatbot (with original/restored content)
        # Filter out system messages for display
        user_messages: list[gr.ChatMessage] = convert_lc2gr_messages(response["messages"])

        # Extract privacy-protected messages from conversation storage
        privacy_protected_messages: list[gr.ChatMessage] = []
        try:
            # Get privacy-protected messages from storage using the thread_id
            stored_messages: list[BaseMessage] = chat_model.get_encrypted_messages(thread_id=thread_id)
            logger.debug(f"Retrieved {len(stored_messages)} stored messages for thread {thread_id}")

            if stored_messages:
                # Filter stored messages to only show user and assistant messages (not system)
                # and get the latest conversation matching the display messages
                display_stored_messages = [m for m in stored_messages if m.type != "system"]
                latest_stored_messages = display_stored_messages[-len(user_messages) :]
                logger.debug(f"Showing last {len(latest_stored_messages)} non-system messages from storage")

                privacy_protected_messages = convert_lc2gr_messages(latest_stored_messages)
            else:
                logger.warning(f"No stored messages found for thread {thread_id}, no messages to show")
                # Fallback: show the same messages but indicate no privacy protection was stored
                privacy_protected_messages = []
        except Exception as e:
            logger.error(f"Error retrieving privacy data: {e}")
            # Error fallback
            privacy_protected_messages = [gr.ChatMessage(role="system", content=f"[Error retrieving privacy data: {e}]")]

        yield user_messages, privacy_protected_messages, browser_state

    return chat_fn
