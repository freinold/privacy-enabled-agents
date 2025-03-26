from logging import getLogger
from uuid import UUID

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.replacement.base import BaseReplacer
from privacy_enabled_agents.storage.base import BaseStorage


class PlaceholderReplacer(BaseReplacer):
    """
    Replacer that replaces entities with placeholders.
    """

    _supported_entities = ["*"]  # This replacer supports all entities

    def __init__(self, storage: BaseStorage) -> None:
        super().__init__(storage)
        self.logger = getLogger(__name__)
        self.logger.info("PlaceholderReplacer initialized.")

    async def replace(self, text: str, entities: list[Entity], context_id: UUID) -> str:
        text_offset = 0

        for entity in entities:
            # Get the replacement for the entity
            replacement = self.storage.get_replacement(entity.text)

            # If the replacement is not found, create a new one
            if replacement is None:
                counter = await self.storage.inc_label_counter(entity.label, context_id)
                formatted_label = entity.label.replace(" ", "_").upper()
                replacement = f"<{formatted_label}_{counter}>"
                await self.storage.put(entity.text, entity.label, replacement, context_id)

            # Replace the entity in the text
            text = text[: entity.start + text_offset] + replacement + text[entity.end + text_offset :]
            text_offset += len(replacement) - len(entity.text)

        return text

    async def restore(self, text: str, context_id: UUID) -> str:
        # Get all replacements for the context_id
        replacements = await self.storage.list_replacements(context_id)

        # Restore the text by replacing placeholders with original text
        for replacement in replacements:
            if replacement in text:
                original_text = await self.storage.get_text(replacement, context_id)
                text = text.replace(replacement, original_text)

        return text
