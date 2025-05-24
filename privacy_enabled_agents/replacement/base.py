from abc import ABC, abstractmethod
from typing import List, Literal
from uuid import UUID

from pydantic import Field

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.storage.base import BaseStorage


class BaseReplacer(ABC):
    """
    Abstract base class for implementing various replacement techniques on different categories of data.

    Provides a common interface for all replacement techniques.
    """

    storage: BaseStorage
    _supported_entities: set[str] | Literal["ANY"] = Field(
        default="ANY",
        description="Supported entities for the replacer.",
    )

    def __init__(self, storage: BaseStorage) -> None:
        self.storage = storage

    def get_supported_entities(self) -> set[str] | Literal["ANY"]:
        """
        Returns the set of entities supported by this replacer.

        Returns:
            set[str] | Literal["ANY"]: The set of supported entities.
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
        text_offset: int = 0

        for entity in entities:
            # Get the replacement for the entity
            replacement: str | None = self.storage.get_replacement(
                text=entity.text,
                context_id=context_id,
            )

            # If the replacement is not found, create a new one
            if replacement is None:
                # Create a new replacement and store it
                replacement = self.create_replacement(entity=entity, context_id=context_id)
                self.storage.put(
                    text=entity.text,
                    label=entity.label,
                    replacement=replacement,
                    context_id=context_id,
                )

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
        replacements: List[str] = self.storage.list_replacements(context_id=context_id)

        # Restore the text by replacing placeholders with original text
        for replacement in replacements:
            if replacement in text:
                original_text: tuple[str, str] | None = self.storage.get_text(replacement, context_id)
                if original_text:
                    text = text.replace(replacement, original_text[0])

        return text

    @abstractmethod
    def create_replacement(self, entity: Entity, context_id: UUID) -> str:
        """
        Creates a replacement for the given entity, based on the entity's label and the context ID to ensure uniqueness.

        Args:
            entity (Entity): The entity to be replaced.
            context_id (UUID): The context ID for the replacement process.

        Returns:
            str: The replacement for the entity.
        """
        pass
