from logging import getLogger

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

    def create_replacement(self, entity: Entity) -> str:
        formatted_label = entity.label.replace(" ", "_").upper()
        counter = self.storage.inc_label_counter(formatted_label)
        return f"<{formatted_label}-{counter}>"
