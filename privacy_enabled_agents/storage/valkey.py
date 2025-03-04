import json
from typing import AsyncIterator, Dict, List, Optional, Tuple
from uuid import UUID

from valkey.asyncio import Valkey

from privacy_enabled_agents.storage.base import BaseStorage


class ValkeyStorage(BaseStorage):
    """
    Implementation of BaseStorage using Valkey as the backend.

    This implementation uses hash sets in Valkey to store replacements with their original
    text and label for each context. Keys are structured as follows:

    - context:{context_id}:{replacement} -> JSON string containing {"text": original_text, "label": original_label}
    - context:{context_id}:replacements -> Set of all replacements for this context
    - contexts -> Set of all context IDs
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

    def _context_key(self, context_id: UUID) -> str:
        """Generate key for a specific context"""
        return f"context:{str(context_id)}"

    def _replacement_key(self, context_id: UUID, replacement: str) -> str:
        """Generate key for a specific replacement in a context"""
        return f"context:{str(context_id)}:{replacement}"

    def _replacements_set_key(self, context_id: UUID) -> str:
        """Generate key for the set of replacements in a context"""
        return f"context:{str(context_id)}:replacements"

    async def put(self, text: str, label: str, replacement: str, context_id: UUID) -> None:
        """
        Stores the given triple of text, label, and replacement.
        """
        # Create a JSON string with the original text and label
        data = json.dumps({"text": text, "label": label})

        # Use a pipeline for atomic operations
        async with self.client.pipeline() as pipe:
            # Store the replacement data
            pipe.set(self._replacement_key(context_id, replacement), data)
            # Add the replacement to the set of replacements for this context
            pipe.sadd(self._replacements_set_key(context_id), replacement)
            # Add the context_id to the set of all contexts
            pipe.sadd("contexts", str(context_id))
            # Execute all commands
            await pipe.execute()

    async def get(self, replacement: str, context_id: UUID) -> tuple[str, str]:
        """
        Retrieves the original text and label of the given replacement.
        """
        data = await self.client.get(self._replacement_key(context_id, replacement))
        if not data:
            raise ValueError(f"Replacement '{replacement}' not found in context {context_id}")

        # Parse the JSON string to get the original text and label
        parsed_data = json.loads(data)
        return parsed_data["text"], parsed_data["label"]

    async def delete(self, replacement: str, context_id: UUID) -> None:
        """
        Deletes the given replacement from storage.
        """
        # Check if the replacement exists
        if not await self.exists(replacement, context_id):
            raise ValueError(f"Replacement '{replacement}' not found in context {context_id}")

        # Use a pipeline for atomic operations
        async with self.client.pipeline() as pipe:
            # Delete the replacement data
            pipe.delete(self._replacement_key(context_id, replacement))
            # Remove the replacement from the set of replacements for this context
            pipe.srem(self._replacements_set_key(context_id), replacement)
            # Execute all commands
            await pipe.execute()

    async def clear(self, context_id: UUID = None) -> None:
        """
        Clears the whole storage or just a specific context.
        """
        if context_id is not None:
            # Clear only the specified context
            replacements = await self.list_replacements(context_id)
            if replacements:
                # Use a pipeline for efficient deletion
                async with self.client.pipeline() as pipe:
                    # Delete each replacement in this context
                    for replacement in replacements:
                        pipe.delete(self._replacement_key(context_id, replacement))

                    # Delete the set of replacements for this context
                    pipe.delete(self._replacements_set_key(context_id))
                    # Remove this context from the set of all contexts
                    pipe.srem("contexts", str(context_id))
                    # Execute all commands
                    await pipe.execute()
        else:
            # Clear all data - get all contexts first
            contexts_data = await self.client.smembers("contexts")
            if contexts_data:
                contexts = [UUID(c.decode("utf-8")) for c in contexts_data]

                # Use a pipeline for efficient deletion
                async with self.client.pipeline() as pipe:
                    # For each context, delete its data
                    for ctx in contexts:
                        replacements = await self.list_replacements(ctx)
                        for replacement in replacements:
                            pipe.delete(self._replacement_key(ctx, replacement))
                        pipe.delete(self._replacements_set_key(ctx))

                    # Delete the set of all contexts
                    pipe.delete("contexts")
                    # Execute all commands
                    await pipe.execute()

    async def exists(self, replacement: str, context_id: UUID) -> bool:
        """
        Checks if a replacement exists in the storage.
        """
        return bool(await self.client.exists(self._replacement_key(context_id, replacement)))

    async def list_replacements(self, context_id: UUID) -> List[str]:
        """
        Lists all replacements for a specific context.
        """
        replacements = await self.client.smembers(self._replacements_set_key(context_id))
        # Convert from bytes to string
        return [r.decode("utf-8") for r in replacements] if replacements else []

    async def get_all_context_data(self, context_id: UUID) -> Dict[str, Tuple[str, str]]:
        """
        Gets all data for a specific context.
        """
        result = {}
        replacements = await self.list_replacements(context_id)

        if replacements:
            # Use a pipeline for batch retrieval
            async with self.client.pipeline() as pipe:
                for replacement in replacements:
                    pipe.get(self._replacement_key(context_id, replacement))

                values = await pipe.execute()

                for i, replacement in enumerate(replacements):
                    if values[i]:
                        data = json.loads(values[i])
                        result[replacement] = (data["text"], data["label"])

        return result

    async def get_stats(self) -> Dict[str, int]:
        """
        Gets statistics about the storage.
        """
        stats = {}

        # Get count of contexts
        contexts_data = await self.client.smembers("contexts")
        num_contexts = len(contexts_data) if contexts_data else 0
        stats["contexts"] = num_contexts

        # Get count of entries across all contexts
        total_entries = 0
        if contexts_data:
            for context_id_bytes in contexts_data:
                context_id = UUID(context_id_bytes.decode("utf-8"))
                replacements = await self.list_replacements(context_id)
                total_entries += len(replacements)

        stats["total_entries"] = total_entries
        return stats

    async def iterate_entries(self, context_id: Optional[UUID] = None) -> AsyncIterator[Tuple[str, str, str, UUID]]:
        """
        Iterates through all entries in the storage.
        """
        if context_id is not None:
            # Iterate through entries for a specific context
            replacements = await self.list_replacements(context_id)
            for replacement in replacements:
                try:
                    text, label = await self.get(replacement, context_id)
                    yield (text, label, replacement, context_id)
                except ValueError:
                    # Skip if entry was deleted during iteration
                    continue
        else:
            # Iterate through entries for all contexts
            contexts_data = await self.client.smembers("contexts")
            if contexts_data:
                for context_id_bytes in contexts_data:
                    ctx_id = UUID(context_id_bytes.decode("utf-8"))
                    async for entry in self.iterate_entries(ctx_id):
                        yield entry

    async def close(self) -> None:
        """
        Close the connection to the Valkey server.
        This should be called when the storage is no longer needed to prevent resource leaks.
        """
        # Update to use aclose() instead of deprecated close() method
        await self.client.aclose()
