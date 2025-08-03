from typing import Literal
from uuid import UUID

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.replacement.base import BaseReplacer


class HashReplacer(BaseReplacer):
    """
    Replacer that replaces entities with their hash values.
    """

    _supported_entities: set[str] | Literal["ANY"] = "ANY"  # Allow all entities

    def create_replacement(self, entity: Entity, context_id: UUID) -> str:
        return hex(hash(entity.text + str(context_id)))
