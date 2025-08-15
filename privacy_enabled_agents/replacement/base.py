from abc import ABC, abstractmethod
from typing import Literal
from uuid import UUID

from pydantic import Field

from privacy_enabled_agents import Entity
from privacy_enabled_agents.storage import BaseEntityStorage


class BaseReplacer(ABC):
    """
    Abstract base class for implementing various replacement techniques on different categories of data.

    Provides a common interface for all replacement techniques.
    """

    entity_storage: BaseEntityStorage
    _supported_entities: set[str] | Literal["ANY"] = Field(
        default="ANY",
        description="Supported entities for the replacer.",
    )

    def __init__(self, entity_storage: BaseEntityStorage) -> None:
        self.entity_storage = entity_storage

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

    def replace(self, text: str, entities: list[Entity], thread_id: UUID) -> str:
        """
        Replaces the given entities in the text.

        Args:
            text (str): The text to be processed.
            entities (list[Entity]): The entities to be replaced.
            thread_id (UUID): The context ID for the replacement process.

        Returns:
            str: The text with the entities replaced.
        """
        text_offset: int = 0

        for entity in entities:
            # Get the replacement for the entity
            replacement: str | None = self.entity_storage.get_replacement(
                text=entity.text,
                thread_id=thread_id,
            )

            # If the replacement is not found, create a new one
            if replacement is None:
                # Create a new replacement and store it
                replacement = self.create_replacement(entity=entity, thread_id=thread_id)
                self.entity_storage.put(
                    text=entity.text,
                    label=entity.label,
                    replacement=replacement,
                    thread_id=thread_id,
                )

            # Replace the entity in the text
            text = text[: entity.start + text_offset] + replacement + text[entity.end + text_offset :]
            text_offset += len(replacement) - len(entity.text)

        return text

    def restore(self, text: str, thread_id: UUID) -> str:
        """
        Restores the replaced entities in the text.

        Args:
            text (str): The text to be processed.
            thread_id (UUID): The context ID for the restoration process.

        Returns:
            str: The text with the entities restored.
        """
        # Get all replacements for the thread_id
        replacements: list[str] = self.entity_storage.list_replacements(thread_id=thread_id)

        # Sort replacements by length (descending) to handle substring issues
        # e.g., <PERSON-10> should be processed before <PERSON-1>
        replacements.sort(key=len, reverse=True)

        # Restore the text by replacing placeholders with original text
        for replacement in replacements:
            if replacement in text:
                original_text: tuple[str, str] | None = self.entity_storage.get_text(replacement, thread_id)
                if original_text:
                    text = text.replace(replacement, original_text[0])

        return text

    @abstractmethod
    def create_replacement(self, entity: Entity, thread_id: UUID) -> str:
        """
        Creates a replacement for the given entity, based on the entity's label and the context ID to ensure uniqueness.

        Args:
            entity (Entity): The entity to be replaced.
            thread_id (UUID): The context ID for the replacement process.

        Returns:
            str: The replacement for the entity.
        """
        pass
