from abc import ABC, abstractmethod
from uuid import UUID

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.storage.base import BaseStorage


class BaseReplacer(ABC):
    """
    Abstract base class for implementing various replacement techniques on different categories of data.

    Provides a common interface for all replacement techniques.
    """

    storage: BaseStorage
    _supported_entities: list[str]  # Can include "*" to indicate support for all entities

    def __init__(self, storage: BaseStorage) -> None:
        self.storage = storage

    def get_supported_entities(self) -> list[str]:
        """
        Returns the list of entities supported by this replacer.
        If the list contains "*", the replacer supports all entities.

        Returns:
            list[str]: The list of supported entities.
        """
        return self._supported_entities

    def validate_entities(self, entities: list[Entity]) -> bool:
        """
        Validates the entities to be replaced.
        If _supported_entities contains "*", all entities are considered valid.

        Args:
            entities (list[Entity]): The entities to be validated.

        Returns:
            bool: True if the entities are supported, False otherwise.
        """
        if "*" in self._supported_entities:
            return True
        return all(entity.label in self._supported_entities for entity in entities)

    @abstractmethod
    def replace(self, text: str, entities: list[Entity], context_id: UUID) -> str:
        """
        Replaces the given entities in the text.

        Args:
            text (str): The text to be processed.
            entities (list[Entity]): The entities to be replaced.
            context_id (UUID): The context ID for the replacement process.

        Returns:
            str: The text with the entities replaced.
        """
        pass

    @abstractmethod
    def restore(self, text: str, context_id: UUID) -> str:
        """
        Restores the replaced entities in the text.

        Args:
            text (str): The text to be processed.
            context_id (UUID): The context ID for the restoration process.

        Returns:
            str: The text with the entities restored.
        """
        pass
