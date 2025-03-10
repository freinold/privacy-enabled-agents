from typing import Dict, Iterator, List, Optional, Tuple
from uuid import UUID

from privacy_enabled_agents.storage.base import BaseStorage


class MemoryStorage(BaseStorage):
    """
    Implementation of BaseStorage that stores all data in process memory.

    This implementation uses a nested dictionary to store replacements with their original
    text and label for each context. The structure is:

    self._data = {
        context_id: {
            replacement: (text, label)
        }
    }
    """

    def __init__(self):
        """
        Initializes the memory storage.
        """
        self._data: Dict[UUID, Dict[str, Tuple[str, str]]] = {}

    async def put(self, text: str, label: str, replacement: str, context_id: UUID) -> None:
        """
        Stores the given triple of text, label, and replacement.

        Args:
            text (str): The original text of the entity.
            label (str): The label / class of the entity.
            replacement (str): The replacement for the entity.
            context_id (UUID): UUID that identifies the specific context (e.g. a conversation).
        """
        if context_id not in self._data:
            self._data[context_id] = {}
        self._data[context_id][replacement] = (text, label)

    async def get(self, replacement: str, context_id: UUID) -> tuple[str, str]:
        """
        Retrieves the original text and label of the given replacement.

        Args:
            replacement (str): The replacement to get the original text and label for.
            context_id (UUID): UUID that identifies the specific context (e.g. a conversation).

        Returns:
            tuple[str, str]: The original text and label of the replacement.

        Raises:
            ValueError: If the replacement is not found in storage.
        """
        if context_id not in self._data or replacement not in self._data[context_id]:
            raise ValueError(f"Replacement '{replacement}' not found in context {context_id}")
        return self._data[context_id][replacement]

    async def delete(self, replacement: str, context_id: UUID) -> None:
        """
        Deletes the given replacement from storage.

        Args:
            replacement (str): The replacement to delete.
            context_id (UUID): UUID that identifies the specific context (e.g. a conversation).

        Raises:
            ValueError: If the replacement is not found in storage
        """
        if not await self.exists(replacement, context_id):
            raise ValueError(f"Replacement '{replacement}' not found in context {context_id}")
        del self._data[context_id][replacement]

    async def clear(self, context_id: UUID = None) -> None:
        """
        Clears the whole storage or just a specific context.

        Args:
            context_id (UUID, optional): If provided, only clears data for this context.
                                       If None, clears all data. Defaults to None.
        """
        if context_id is not None:
            if context_id in self._data:
                del self._data[context_id]
        else:
            self._data.clear()

    async def exists(self, replacement: str, context_id: UUID) -> bool:
        """
        Checks if a replacement exists in the storage.

        Args:
            replacement (str): The replacement to check.
            context_id (UUID): UUID that identifies the specific context.

        Returns:
            bool: True if the replacement exists, False otherwise.
        """
        return context_id in self._data and replacement in self._data[context_id]

    async def list_replacements(self, context_id: UUID) -> List[str]:
        """
        Lists all replacements for a specific context.

        Args:
            context_id (UUID): UUID that identifies the specific context.

        Returns:
            List[str]: List of all replacements for the context.
        """
        if context_id not in self._data:
            return []
        return list(self._data[context_id].keys())

    async def get_all_context_data(self, context_id: UUID) -> Dict[str, Tuple[str, str]]:
        """
        Gets all data for a specific context.

        Args:
            context_id (UUID): UUID that identifies the specific context.

        Returns:
            Dict[str, Tuple[str, str]]: Dictionary mapping replacements to (text, label) tuples.
        """
        if context_id not in self._data:
            return {}
        return self._data[context_id].copy()

    async def get_stats(self) -> Dict[str, int]:
        """
        Gets statistics about the storage.

        Returns:
            Dict[str, int]: Dictionary with statistics (e.g., total entries, contexts).
        """
        total_entries = sum(len(context_data) for context_data in self._data.values())
        return {"contexts": len(self._data), "total_entries": total_entries}

    async def iterate_entries(self, context_id: Optional[UUID] = None) -> Iterator[Tuple[str, str, str, UUID]]:
        """
        Iterates through all entries in the storage.

        Args:
            context_id (Optional[UUID]): If provided, only iterate through entries for this context.

        Returns:
            Iterator[Tuple[str, str, str, UUID]]: Iterator of (text, label, replacement, context_id) tuples.
        """
        if context_id is not None:
            if context_id in self._data:
                for replacement, (text, label) in self._data[context_id].items():
                    yield (text, label, replacement, context_id)
        else:
            for ctx_id, ctx_data in self._data.items():
                for replacement, (text, label) in ctx_data.items():
                    yield (text, label, replacement, ctx_id)

    async def close(self) -> None:
        """
        No resources to close for in-memory storage, but implementing for interface consistency.
        """
        pass
