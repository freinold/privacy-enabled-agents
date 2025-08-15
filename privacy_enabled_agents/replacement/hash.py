from typing import Literal
from uuid import UUID

from privacy_enabled_agents import Entity

from .base import BaseReplacer


class HashReplacer(BaseReplacer):
    """
    Replacer that replaces entities with their hash values.
    """

    _supported_entities: set[str] | Literal["ANY"] = "ANY"  # Allow all entities

    def create_replacement(self, entity: Entity, thread_id: UUID) -> str:
        return hex(hash(entity.text + str(thread_id)))
