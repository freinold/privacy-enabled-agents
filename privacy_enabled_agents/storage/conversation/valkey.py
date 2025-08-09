import json
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from valkey import Valkey

from privacy_enabled_agents.storage.conversation import BaseConversationStorage


class ValkeyConversationStorage(BaseConversationStorage):
    """
    Implementation of BaseConversationStorage using Valkey as the backend.

    This implementation stores conversation messages with privacy-protected content.
    Keys are structured as follows:

    - conv:{thread_id}:messages -> List of all messages for this conversation thread
    - convs -> Set of all conversation thread IDs
    """

    client: Valkey

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, **kwargs):
        """
        Initializes the Valkey conversation storage.

        Args:
            host (str): Host where Valkey server is running.
            port (int): Port of the Valkey server.
            db (int): Database number to use (should match entity storage for same instance).
            **kwargs: Additional arguments to pass to Valkey client.
        """
        self.client = Valkey(host=host, port=port, db=db, **kwargs)

    def _conversation_messages_key(self, thread_id: UUID) -> str:
        """Generate key for all messages in a conversation thread"""
        return f"conv:{thread_id}:messages"

    def _conversations_set_key(self) -> str:
        """Generate key for the set of all conversation thread IDs"""
        return "convs"

    def _serialize_message(self, message: BaseMessage) -> str:
        """Serialize a message to JSON string"""
        return json.dumps(
            {
                "type": message.__class__.__name__,
                "content": message.content,
                "id": message.id,
                "additional_kwargs": getattr(message, "additional_kwargs", {}),
                "response_metadata": getattr(message, "response_metadata", {}),
            }
        )

    def _deserialize_message(self, message_str: str) -> BaseMessage:
        """Deserialize a message from JSON string"""
        data = json.loads(message_str)
        message_type = data["type"]

        # Create the appropriate message type
        if message_type == "HumanMessage":
            msg = HumanMessage(content=data["content"])
        elif message_type == "AIMessage":
            msg = AIMessage(content=data["content"])
        else:
            # Fallback to HumanMessage for unknown types
            msg = HumanMessage(content=data["content"])

        # Restore additional attributes
        msg.id = data.get("id")
        if "additional_kwargs" in data:
            msg.additional_kwargs = data["additional_kwargs"]
        if "response_metadata" in data:
            msg.response_metadata = data["response_metadata"]

        return msg

    def store_encrypted_messages(self, thread_id: UUID, messages: list[BaseMessage]) -> None:
        """
        Store encrypted messages for a conversation.

        Args:
            thread_id: UUID identifying the specific conversation thread
            messages: List of messages with privacy placeholders
        """
        if not messages:
            return

        # Serialize messages
        serialized_messages = [self._serialize_message(msg) for msg in messages]

        # Store in conversation-specific key
        conversation_key = self._conversation_messages_key(thread_id)

        # Use pipeline for atomic operations
        pipe = self.client.pipeline()

        # Add messages to conversation
        pipe.lpush(conversation_key, *serialized_messages)

        # Add to conversations set
        pipe.sadd(self._conversations_set_key(), str(thread_id))

        # Execute pipeline
        pipe.execute()

    def get_encrypted_messages(self, thread_id: UUID, limit: int | None = None) -> list[BaseMessage]:
        """
        Retrieve encrypted messages for a conversation.

        Args:
            thread_id: UUID identifying the specific conversation thread
            limit: Maximum number of messages to retrieve (default is None for no limit); starts from the most recent

        Returns:
            List of messages with privacy placeholders
        """
        conversation_key = self._conversation_messages_key(thread_id)

        # Get messages (most recent first due to lpush)
        if limit is None:
            message_strs: list[bytes] = self.client.lrange(conversation_key, 0, -1)  # type: ignore
        else:
            message_strs = self.client.lrange(conversation_key, 0, limit - 1)  # type: ignore

        # Deserialize messages
        messages = []
        for msg_str in message_strs:
            try:
                messages.append(self._deserialize_message(msg_str.decode("utf-8")))
            except (json.JSONDecodeError, KeyError) as e:
                # Skip invalid messages
                print(f"Warning: Failed to deserialize message: {e}")
                continue

        # Reverse to get chronological order (oldest first)
        return list(reversed(messages))

    def clear_conversation(self, thread_id: UUID) -> None:
        """
        Clear all encrypted messages for a specific conversation.

        Args:
            thread_id: UUID identifying the specific conversation thread
        """
        pipe = self.client.pipeline()

        # Clear conversation data
        conversation_key = self._conversation_messages_key(thread_id)
        pipe.delete(conversation_key)
        pipe.srem(self._conversations_set_key(), str(thread_id))

        pipe.execute()

    def conversation_exists(self, thread_id: UUID) -> bool:
        """
        Check if a conversation exists in storage.

        Args:
            thread_id: UUID identifying the specific conversation thread

        Returns:
            True if conversation exists, False otherwise
        """
        conversation_key = self._conversation_messages_key(thread_id)
        result: int = self.client.exists(conversation_key)  # type: ignore
        return result > 0
