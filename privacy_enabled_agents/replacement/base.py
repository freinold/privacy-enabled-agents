from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.storage.base import BaseStorage


class BaseReplacer(ABC):
    storage: BaseStorage

    """
    Abstract base class for implementing various replacement techniques on different categories of data.

    Provides a common interface for all replacement techniques.
    """

    def __init__(self, storage: BaseStorage) -> None:
        self.storage = storage

    @abstractmethod
    def replace(self, text: str, entities: list[Entity], context_id: Optional[UUID] = None) -> str:
        """
        Replaces the given entities in the text.

        Args:
            text (str): The text to be processed.
            entities (list[Entity]): The entities to be replaced.
            context_id (Optional[UUID]): The context ID for the replacement process, if not provided, no restoration will be possible.

        Returns:
            str: The text with the entities replaced.
        """
        pass

    @abstractmethod
    def restore(self, text: str, context_id: UUID) -> str:
        """
        Restores the replaced entities in the text.

        Args:
            text (str): The text to be processed.
            context_id (UUID): The context ID for the restoration process.

        Returns:
            str: The text with the entities restored.
        """
        pass
