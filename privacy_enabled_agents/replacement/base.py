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
        text_offset = 0

        for entity in entities:
            # Get the replacement for the entity
            replacement = self.storage.get_replacement(entity.text)

            # If the replacement is not found, create a new one
            if replacement is None:
                # Create a new replacement and store it
                replacement = self.create_replacement(entity)
                self.storage.put(entity.text, entity.label, replacement, context_id)

            # Replace the entity in the text
            text = text[: entity.start + text_offset] + replacement + text[entity.end + text_offset :]
            text_offset += len(replacement) - len(entity.text)

        return text

    def restore(self, text: str, context_id: UUID) -> str:
        """
        Restores the replaced entities in the text.

        Args:
            text (str): The text to be processed.
            context_id (UUID): The context ID for the restoration process.

        Returns:
            str: The text with the entities restored.
        """
        # Get all replacements for the context_id
        replacements = self.storage.list_replacements(context_id)

        # Restore the text by replacing placeholders with original text
        for replacement in replacements:
            if replacement in text:
                original_text = self.storage.get_text(replacement, context_id)
                text = text.replace(replacement, original_text)

        return text

    @abstractmethod
    def create_replacement(self, entity: Entity) -> str:
        """
        Creates a replacement for the given entity.

        Args:
            entity (Entity): The entity to be replaced.

        Returns:
            str: The replacement for the entity.
        """
        pass
