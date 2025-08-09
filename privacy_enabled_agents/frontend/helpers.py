from collections.abc import Callable

from gradio import ChatMessage


# TODO: Enhance and use this in frontend
def create_chat_function() -> Callable[[str, list[ChatMessage]], list[ChatMessage]]:
    def chat_fn(message: str, history: list[ChatMessage]) -> list[ChatMessage]:
        # Add the user message to history
        history.append(ChatMessage(role="user", content=message))
        # Add the assistant response to history
        history.append(ChatMessage(role="assistant", content=f"Echo: {message}"))
        return history

    return chat_fn
