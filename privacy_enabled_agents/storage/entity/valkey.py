import json
from collections.abc import Iterator
from uuid import UUID

from valkey import Valkey

from privacy_enabled_agents.storage.entity import BaseEntityStorage


class ValkeyEntityStorage(BaseEntityStorage):
    """
    Implementation of BaseEntityStorage using Valkey as the backend.

    This implementation uses hash sets in Valkey to store replacements with their original
    text and label for each context. Keys are structured as follows:

    - ctx:{thread_id}:reps -> Set of all replacements for this context
    - ctx:{thread_id}:rep:{replacement} -> JSON string containing {"text": original_text, "label": original_label}
    - ctx:{thread_id}:tex2rep -> Hash map mapping original_text to replacement
    - ctx:{thread_id}:lc:{label} -> Label counter for this label
    - ctxs -> Set of all context IDs
    """

    client: Valkey

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, **kwargs):
        """
        Initializes the Valkey storage.

        Args:
            host (str): Host where Valkey server is running.
            port (int): Port of the Valkey server.
            db (int): Database number to use.
            **kwargs: Additional arguments to pass to Valkey client.
        """
        self.client = Valkey(host=host, port=port, db=db, **kwargs)

    def _replacement_key(self, thread_id: UUID, replacement: str) -> str:
        """Generate key for a specific replacement in a context"""
        return f"ctx:{thread_id}:rep:{replacement}"

    def _replacements_set_key(self, thread_id: UUID) -> str:
        """Generate key for the set of replacements in a context"""
        return f"ctx:{thread_id}:reps"

    def _text_to_replacement_key(self, thread_id: UUID) -> str:
        """Generate key for the hash mapping text to replacement in a context"""
        return f"ctx:{thread_id}:tex2rep"

    def _label_counter_key(self, thread_id: UUID, label: str) -> str:
        """Generate key for the label counter in a context"""
        return f"ctx:{thread_id}:lc:{label}"

    def put(self, text: str, label: str, replacement: str, thread_id: UUID) -> None:
        # Create a JSON string with the original text and label
        data: str = json.dumps({"text": text, "label": label})

        # Use a pipeline for atomic operations
        with self.client.pipeline() as pipe:
            # Store the replacement data
            pipe.set(self._replacement_key(thread_id, replacement), data)
            # Add the replacement to the set of replacements for this context
            pipe.sadd(self._replacements_set_key(thread_id), replacement)
            # Add to reverse lookup index: map text to replacement
            pipe.hset(self._text_to_replacement_key(thread_id), text, replacement)
            # Add the thread_id to the set of all contexts
            pipe.sadd("ctxs", str(thread_id))
            # Execute all commands
            pipe.execute()

    def inc_label_counter(self, label: str, thread_id: UUID) -> int:
        # Increment the label counter and get the new value
        new_value: int = self.client.incr(self._label_counter_key(thread_id, label))  # type: ignore
        return new_value

    def get_text(self, replacement: str, thread_id: UUID) -> tuple[str, str]:
        data: str | None = self.client.get(self._replacement_key(thread_id, replacement))  # type: ignore
        if data is None:
            raise ValueError(f"Replacement '{replacement}' not found in context {thread_id}")

        # Parse the JSON string to get the original text and label
        parsed_data = json.loads(data)
        return parsed_data["text"], parsed_data["label"]

    def get_replacement(self, text: str, thread_id: UUID) -> str | None:
        # Use the reverse lookup index to directly get the replacement
        replacement: bytes | None = self.client.hget(self._text_to_replacement_key(thread_id), text)  # type: ignore
        if replacement:
            return replacement.decode("utf-8")
        return None

    def delete(self, replacement: str, thread_id: UUID) -> None:
        # Check if the replacement exists
        if not self.exists(replacement, thread_id):
            raise ValueError(f"Replacement '{replacement}' not found in context {thread_id}")

        # Get the original text to remove from the reverse index
        data: str | None = self.client.get(self._replacement_key(thread_id, replacement))  # type: ignore
        if data is None:
            raise ValueError(f"Replacement '{replacement}' not found in context {thread_id}")
        # Parse the JSON to get the original text
        original_text: str | None = json.loads(data)["text"] if data else None

        # Use a pipeline for atomic operations
        with self.client.pipeline() as pipe:
            # Delete the replacement data
            pipe.delete(self._replacement_key(thread_id, replacement))
            # Remove the replacement from the set of replacements for this context
            pipe.srem(self._replacements_set_key(thread_id), replacement)
            # Remove from the reverse lookup index if we found the original text
            if original_text:
                pipe.hdel(self._text_to_replacement_key(thread_id), original_text)
            # Execute all commands
            pipe.execute()

    def clear(self, thread_id: UUID | None = None) -> None:
        if thread_id is not None:
            # Clear only the specified context
            replacements: list[str] = self.list_replacements(thread_id)
            if replacements:
                # Use a pipeline for efficient deletion
                with self.client.pipeline() as pipe:
                    # Delete each replacement in this context
                    for replacement in replacements:
                        pipe.delete(self._replacement_key(thread_id, replacement))

                    # Delete the set of replacements for this context
                    pipe.delete(self._replacements_set_key(thread_id))
                    # Delete the text-to-replacement mapping
                    pipe.delete(self._text_to_replacement_key(thread_id))
                    # Remove this context from the set of all contexts
                    pipe.srem("ctxs", str(thread_id))
                    # Execute all commands
                    pipe.execute()
        else:
            # Clear all data - get all contexts first
            contexts_data: set[bytes] | None = self.client.smembers("ctxs")  # type: ignore
            if contexts_data:
                contexts: list[UUID] = [UUID(c.decode("utf-8")) for c in contexts_data]

                # Use a pipeline for efficient deletion
                with self.client.pipeline() as pipe:
                    # For each context, delete its data
                    for ctx in contexts:
                        replacements = self.list_replacements(ctx)
                        for replacement in replacements:
                            pipe.delete(self._replacement_key(ctx, replacement))
                        pipe.delete(self._replacements_set_key(ctx))
                        pipe.delete(self._text_to_replacement_key(ctx))

                    # Delete the set of all contexts
                    pipe.delete("ctxs")
                    # Execute all commands
                    pipe.execute()

    def exists(self, replacement: str, thread_id: UUID) -> bool:
        return bool(self.client.exists(self._replacement_key(thread_id, replacement)))

    def list_replacements(self, thread_id: UUID) -> list[str]:
        replacements: set[bytes] | None = self.client.smembers(self._replacements_set_key(thread_id))  # type: ignore
        # Convert from bytes to string
        return [r.decode("utf-8") for r in replacements] if replacements else []

    def get_all_context_data(self, thread_id: UUID) -> dict[str, tuple[str, str]]:
        result: dict[str, tuple[str, str]] = {}
        replacements: list[str] = self.list_replacements(thread_id)

        if replacements:
            # Use a pipeline for batch retrieval
            with self.client.pipeline() as pipe:
                for replacement in replacements:
                    pipe.get(self._replacement_key(thread_id, replacement))

                values: list[str | None] = pipe.execute()

            for i, replacement in enumerate(replacements):
                if values[i] is not None:
                    data: dict[str, str] = json.loads(values[i])  # type: ignore
                    result[replacement] = (data["text"], data["label"])

        return result

    def get_stats(self) -> dict[str, int]:
        stats: dict[str, int] = {}

        # Get count of contexts
        contexts_data: set[bytes] | None = self.client.smembers("ctxs")  # type: ignore
        num_contexts: int = len(contexts_data) if contexts_data is not None else 0
        stats["contexts"] = num_contexts

        # Get count of entries across all contexts
        total_entries: int = 0
        if contexts_data is not None:
            for thread_id_bytes in contexts_data:
                thread_id = UUID(thread_id_bytes.decode("utf-8"))
                replacements: list[str] = self.list_replacements(thread_id)
                total_entries += len(replacements)

        stats["total_entries"] = total_entries
        return stats

    def iterate_entries(self, thread_id: UUID | None = None) -> Iterator[tuple[str, str, str, UUID]]:
        if thread_id is not None:
            # Iterate through entries for a specific context
            replacements: list[str] = self.list_replacements(thread_id)
            for replacement in replacements:
                try:
                    text: str
                    label: str
                    text, label = self.get_text(replacement, thread_id)
                    yield (text, label, replacement, thread_id)
                except ValueError:
                    # Skip if entry was deleted during iteration
                    continue
        else:
            # Iterate through entries for all contexts
            contexts_data: set[bytes] | None = self.client.smembers("contexts")  # type: ignore
            if contexts_data is not None:
                for thread_id_bytes in contexts_data:
                    ctx_id = UUID(thread_id_bytes.decode("utf-8"))
                    for entry in self.iterate_entries(ctx_id):
                        yield entry

    def close(self) -> None:
        self.client.close()

    def __del__(self):
        self.close()
