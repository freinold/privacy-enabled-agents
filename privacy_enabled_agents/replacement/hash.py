from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.replacement.base import BaseReplacer


class HashReplacer(BaseReplacer):
    """
    Replacer that replaces entities with their hash values.
    """

    _supported_entities = ["*"]  # This replacer supports all entities

    def create_replacement(self, entity: Entity) -> str:
        return hex(hash(entity.text))[:2]
