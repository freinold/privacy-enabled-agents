from typing import Literal
from uuid import UUID

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.replacement.base import BaseReplacer


class PlaceholderReplacer(BaseReplacer):
    """
    Replacer that replaces entities with placeholders.
    """

    _supported_entities: set[str] | Literal["ANY"] = "ANY"  # Allow all entities

    def create_replacement(self, entity: Entity, thread_id: UUID) -> str:
        formatted_label: str = entity.label.replace(" ", "_").upper()
        counter: int = self.storage.inc_label_counter(formatted_label, thread_id)
        return f"[{formatted_label}_{counter:02d}]"
