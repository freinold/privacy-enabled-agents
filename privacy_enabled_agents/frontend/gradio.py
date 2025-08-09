from logging import Logger, getLogger
from typing import Any, Literal
from uuid import uuid4

import gradio as gr
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.messages.base import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_mistralai import ChatMistralAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph.state import CompiledStateGraph

from privacy_enabled_agents.chat_models import PrivacyEnabledChatModel
from privacy_enabled_agents.detection import RemoteGlinerDetector
from privacy_enabled_agents.examples import create_basic_agent
from privacy_enabled_agents.replacement import PlaceholderReplacer
from privacy_enabled_agents.storage import ValkeyConversationStorage, ValkeyEntityStorage

# Create logger for this module
logger: Logger = getLogger(__name__)


def create_gradio_interface() -> gr.Blocks:
    langfuse_handler = CallbackHandler()

    chat_model: BaseChatModel = ChatMistralAI(model="mistral-medium-2506")  # type: ignore[unknown-argument]
    detector = RemoteGlinerDetector(
        supported_entities={"person name", "location", "organization", "address", "email", "phone"},
    )
    storage = ValkeyEntityStorage()
    conversation_storage = ValkeyConversationStorage()
    replacer = PlaceholderReplacer(storage=storage)

    privacy_chat_model = PrivacyEnabledChatModel(
        model=chat_model,
        replacer=replacer,
        detector=detector,
        conversation_storage=conversation_storage,
    )

    with RedisSaver.from_conn_string("redis://localhost:6380") as checkpointer:
        checkpointer.setup()

        agent: CompiledStateGraph = create_basic_agent(
            chat_model=privacy_chat_model,
            checkpointer=checkpointer,
            runnable_config=RunnableConfig(callbacks=[langfuse_handler]),
        )

    message_type_map: dict[str, Literal["user", "assistant", "system"]] = {
        "human": "user",
        "ai": "assistant",
        "system": "system",
    }

    def chat_fn(message: str, browser_state: dict, history: list[gr.ChatMessage]):
        # Get thread_id from browser state (should already be set by load event)
        thread_id: str | None = browser_state.get("thread_id")
        if not thread_id:
            # This should not happen if load event worked properly, but fallback
            thread_id = str(uuid4())
            browser_state = {"thread_id": thread_id}

        logger.info(f"Chat function called with thread_id: {thread_id}")

        # Add the user message to history immediately for the left chat
        user_message = gr.ChatMessage(role="user", content=message)
        updated_history = history + [user_message]

        # Yield the user message immediately
        yield updated_history, [], browser_state

        input: dict[str, Any] = {"messages": [HumanMessage(content=message)]}
        response: dict[str, Any] = agent.invoke(input, config={"configurable": {"thread_id": thread_id}})

        logger.debug(f"Agent response contains {len(response['messages'])} messages")

        # Extract all messages for the user-facing chatbot (with original/restored content)
        # Filter out system messages for display
        display_messages = [m for m in response["messages"] if m.type != "system"]
        user_messages: list[gr.ChatMessage] = [gr.ChatMessage(role=message_type_map[m.type], content=m.content) for m in display_messages]

        # Extract privacy-protected messages from conversation storage
        privacy_protected_messages: list[gr.ChatMessage] = []
        try:
            # Get privacy-protected messages from storage using the thread_id
            stored_messages: list[BaseMessage] = privacy_chat_model.get_encrypted_messages(thread_id=thread_id)
            logger.debug(f"Retrieved {len(stored_messages)} stored messages for thread {thread_id}")

            if stored_messages:
                # Filter stored messages to only show user and assistant messages (not system)
                # and get the latest conversation matching the display messages
                display_stored_messages = [m for m in stored_messages if m.type != "system"]
                latest_stored_messages = display_stored_messages[-len(user_messages) :]
                logger.debug(f"Showing last {len(latest_stored_messages)} non-system messages from storage")

                privacy_protected_messages = [
                    gr.ChatMessage(role=message_type_map[m.type], content=m.content) for m in latest_stored_messages
                ]
            else:
                logger.warning(f"No stored messages found for thread {thread_id}, using current response messages")
                # Fallback: show the same messages but indicate no privacy protection was stored
                privacy_protected_messages = [
                    gr.ChatMessage(role=message_type_map[m.type], content=f"[Privacy data not stored] {m.content}")
                    for m in response["messages"]
                ]
        except Exception as e:
            logger.error(f"Error retrieving privacy data: {e}")
            # Error fallback
            privacy_protected_messages = [gr.ChatMessage(role="system", content=f"[Error retrieving privacy data: {e}]")]

        yield user_messages, privacy_protected_messages, browser_state

    with gr.Blocks() as demo:
        demo.title = "Privacy Enabled Agents"

        with gr.Tab(label="Basic Agent"):
            gr.Markdown("### Basic Agent with Privacy Features")
            with gr.Row():
                with gr.Column(scale=6):
                    user_side_chatbot: gr.Chatbot = gr.Chatbot(type="messages", label="Privacy-Preserving Chatbot")
                with gr.Column(scale=6):
                    real_conversation: gr.Chatbot = gr.Chatbot(type="messages", label="Real Conversation")
            with gr.Row():
                user_input: gr.Textbox = gr.Textbox(label="User Input", placeholder="Type your message here...")

            # Create BrowserState with proper storage key
            browser_state = gr.BrowserState(storage_key="privacy_agent_session")

            user_input.submit(
                chat_fn,
                inputs=[user_input, browser_state, user_side_chatbot],
                outputs=[user_side_chatbot, real_conversation, browser_state],
            ).then(
                lambda: "",  # Clear the input after submission
                outputs=[user_input],
            )

            # Load existing session from browser state when page loads
            @demo.load(inputs=[browser_state], outputs=[browser_state])
            def load_existing_session(saved_state):
                if saved_state and saved_state.get("thread_id"):
                    logger.info(f"Loading existing session with thread_id: {saved_state['thread_id']}")
                    return saved_state
                else:
                    # Generate new thread_id for new session
                    new_thread_id = str(uuid4())
                    logger.info(f"Creating new session with thread_id: {new_thread_id}")
                    return {"thread_id": new_thread_id}

    return demo

    # with Blocks() as demo:
    #     start_messages = [
    #         ChatMessage(role="assistant", content="How can I assist you today?"),
    #     ]
    #     Markdown("## Privacy enabled Agents")
    #     with Tab(label="Basic Agent"):
    #         Markdown("### Basic Agent with Privacy Features")
    #         with Row():
    #             with Column(scale=6):
    #                 with Row():
    #                     with Column():
    #                         Chatbot(
    #                             label="Privacy-Preserving Chatbot",
    #                             type="messages",
    #                             height=650,
    #                             value=start_messages,  # type: ignore
    #                         )
    #                     with Column():
    #                         Chatbot(
    #                             label="Real Conversation",
    #                             type="messages",
    #                             height=650,
    #                             value=start_messages,  # type: ignore
    #                         )
    #                 with Row():
    #                     Textbox(
    #                         label="User Input",
    #                         placeholder="Type your message here...",
    #                     )
    #             with Column(scale=2):
    #                 with Accordion(label="Agent Details", open=False):
    #                     with Group():
    #                         JSON(label="Agent State", height=300)
    #                         JSON(label="Entity Collection", height=300)

    #     with Tab(label="Test ChatInterface"):
    #         ChatInterface(fn=lambda x: f"You said: {x}")
    #     # with Tab(label="Websearch Agent"):
    #     #     with Row():
    #     #         with Column():
    #     #             Chatbot(label="Privacy-Preserving Chatbot", type="messages", height=400)
    #     #         with Column():
    #     #             Chatbot(label="Real Conversation", type="messages", height=400)
    #     # with Tab(label="Medical Agent"):
    #     #     with Row():
    #     #         with Column():
    #     #             Chatbot(label="Privacy-Preserving Chatbot", type="messages", height=400)
    #     #         with Column():
    #     #             Chatbot(label="Real Conversation", type="messages", height=400)
    #     # with Tab(label="Financial Agent"):
    #     #     with Row():
    #     #         with Column():
    #     #             Chatbot(label="Privacy-Preserving Chatbot", type="messages", height=400)
    #     #         with Column():
    #     #             Chatbot(label="Real Conversation", type="messages", height=400)
    #     # with Tab(label="Public Service Agent"):
    #     #     with Row():
    #     #         with Column():
    #     #             Chatbot(label="Privacy-Preserving Chatbot", type="messages", height=400)
    #     #         with Column():
    #     #             Chatbot(label="Real Conversation", type="messages", height=400)
    # return demo
