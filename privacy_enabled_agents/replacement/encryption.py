from typing import Literal
from uuid import UUID

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.replacement.base import BaseReplacer


class MockEncryptionReplacer(BaseReplacer):
    """A replacer only to be used with the EncryptionStorage class."""

    _supported_entities: set[str] | Literal["ANY"] = "ANY"  # Allow all entities  # noqa: F821

    def create_replacement(self, entity: Entity, context_id: UUID) -> str:
        raise NotImplementedError("MockEncryptionReplacer does not support create_replacement operation.")
