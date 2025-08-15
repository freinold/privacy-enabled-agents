from typing import Literal
from uuid import UUID

from privacy_enabled_agents import Entity

from .base import BaseReplacer


class MockEncryptionReplacer(BaseReplacer):
    """A replacer only to be used with the EncryptionStorage class."""

    _supported_entities: set[str] | Literal["ANY"] = "ANY"  # Allow all entities  # noqa: F821

    def create_replacement(self, entity: Entity, thread_id: UUID) -> str:
        raise NotImplementedError("MockEncryptionReplacer does not support create_replacement operation.")
