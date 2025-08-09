from abc import ABC, abstractmethod
from uuid import UUID

from langchain_core.messages import BaseMessage


class BaseConversationStorage(ABC):
    """
    Abstract base class for storing privacy-protected conversation messages.

    This storage system maintains redacted conversation messages alongside
    the entity replacement storage, providing a complete audit trail of
    what the LLM actually processed vs. what the user sees.
    """

    @abstractmethod
    def store_encrypted_messages(self, thread_id: UUID, messages: list[BaseMessage]) -> None:
        """
        Store encrypted messages for a conversation.

        Args:
            thread_id: UUID identifying the specific conversation thread
            messages: List of messages with privacy placeholders
        """
        pass

    @abstractmethod
    def get_encrypted_messages(self, thread_id: UUID, limit: int | None = None) -> list[BaseMessage]:
        """
        Retrieve encrypted messages for a conversation.

        Args:
            thread_id: UUID identifying the specific conversation thread
            limit: Maximum number of messages to retrieve (default is None for no limit); starts from the most recent

        Returns:
            List of messages with privacy placeholders
        """
        pass

    @abstractmethod
    def clear_conversation(self, thread_id: UUID) -> None:
        """
        Clear all encrypted messages for a specific conversation.

        Args:
            thread_id: UUID identifying the specific conversation thread
        """
        pass

    @abstractmethod
    def conversation_exists(self, thread_id: UUID) -> bool:
        """
        Check if a conversation exists in storage.

        Args:
            thread_id: UUID identifying the privacy context
            conversation_id: String identifying the specific conversation/thread

        Returns:
            True if conversation exists, False otherwise
        """
        pass
