from abc import ABC, abstractmethod
from collections.abc import Iterator
from uuid import UUID


class BaseStorage(ABC):
    """
    Abstract base class for implementing various storage techniques for storing triples of replacements and their original values and labels.
    """

    @abstractmethod
    def put(self, text: str, label: str, replacement: str, context_id: UUID) -> None:
        """
        Stores the given triple of text, label, and replacement.

        Args:
            text (str): The original text of the entity.
            label (str): The label / class of the entity.
            replacement (str): The replacement for the entity.
            context_id (UUID): UUID that identifies the specific context (e.g. a conversation).
        """
        pass

    @abstractmethod
    def inc_label_counter(self, label: str, context_id: UUID) -> int:
        """
        Increments the counter for the given label.

        Args:
            label (str): The label to increment the counter for.
            context_id (UUID): UUID that identifies the specific context (e.g. a conversation).

        Returns:
            int: The new counter value.
        """
        pass

    @abstractmethod
    def get_text(self, replacement: str, context_id: UUID) -> tuple[str, str] | None:
        """
        Retrieves the original text and label of the given replacement.

        Args:
            replacement (str): The replacement to get the original text and label for.
            context_id (UUID): UUID that identifies the specific context (e.g. a conversation).

        Returns:
            Optional[tuple[str, str]]: The original text and label of the replacement, or None if not found.
        """
        pass

    @abstractmethod
    def get_replacement(self, text: str, context_id: UUID) -> str | None:
        """
        Retrieves the replacement for the given text. If there is no replacement, return None.

        Args:
            text (str): The text to get the replacement for
            context_id (UUID): UUID that identifies the specific context (e.g. a conversation).

        Returns:
            Optional[str]: The replacement for the text, or None if no replacement is found.
        """
        pass

    @abstractmethod
    def clear(self, context_id: UUID | None = None) -> None:
        """
        Clears the whole storage.

        Args:
            context_id (UUID, optional): If provided, only clears data for this context.
                                       If None, clears all data. Defaults to None.
        """
        pass

    @abstractmethod
    def delete(self, replacement: str, context_id: UUID) -> None:
        """
        Deletes the given replacement from storage.

        Args:
            replacement (str): The replacement to delete.
            context_id (UUID): UUID that identifies the specific context (e.g. a conversation).

        Raises:
            ValueError: If the replacement is not found in storage
        """
        pass

    @abstractmethod
    def exists(self, replacement: str, context_id: UUID) -> bool:
        """
        Checks if a replacement exists in the storage.

        Args:
            replacement (str): The replacement to check.
            context_id (UUID): UUID that identifies the specific context.

        Returns:
            bool: True if the replacement exists, False otherwise.
        """
        pass

    @abstractmethod
    def list_replacements(self, context_id: UUID) -> list[str]:
        """
        Lists all replacements for a specific context.

        Args:
            context_id (UUID): UUID that identifies the specific context.

        Returns:
            List[str]: List of all replacements for the context.
        """
        pass

    @abstractmethod
    def get_all_context_data(self, context_id: UUID) -> dict[str, tuple[str, str]]:
        """
        Gets all data for a specific context.

        Args:
            context_id (UUID): UUID that identifies the specific context.

        Returns:
            Dict[str, Tuple[str, str]]: Dictionary mapping replacements to (text, label) tuples.
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, int]:
        """
        Gets statistics about the storage.

        Returns:
            Dict[str, int]: Dictionary with statistics (e.g., total entries, contexts).
        """
        pass

    @abstractmethod
    def iterate_entries(self, context_id: UUID | None = None) -> Iterator[tuple[str, str, str, UUID]]:
        """
        Iterates through all entries in the storage.

        Args:
            context_id (Optional[UUID]): If provided, only iterate through entries for this context.

        Returns:
            Iterator[Tuple[str, str, str, UUID]]: iterator of (text, label, replacement, context_id) tuples.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass
