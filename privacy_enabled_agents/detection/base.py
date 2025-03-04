from abc import ABC, abstractmethod
from typing import Optional, Union

from pydantic import BaseModel, Field

from privacy_enabled_agents.base import Entity


class DetectionResult(BaseModel):
    entities: list[Entity]
    text: str
    threshold: Optional[float] = Field(ge=0.0, le=1.0, default=None)


class BaseDetector(ABC):
    """
    Abstract base class for implementing various detection techniques on different categories of data.

    Provides a common interface for all detection techniques.
    """

    def __init__(self, supported_entities: list[str]) -> None:
        self.supported_entities = supported_entities

    @abstractmethod
    def detect(self, texts: Union[str, list[str]], threshold: Optional[float] = None) -> list[DetectionResult]:
        """
        Detects entities in the given text.

        Args:
            texts (Union[str, list[str]]): The text or list of texts to be analyzed.
            threshold (Optional[float]): The threshold for the detection process. Not all detectors may use this parameter.

        Returns:
            list[DetectionResult]: A list of DetectionResults containing the detected entities.
        """
        pass

    def validate_input(self, texts: Union[str, list[str]]) -> None:
        """
        Validates the input text.

        Args:
            text (str): The text to be validated.

        Raises:
            ValueError: If the input is not valid.
        """
        if isinstance(texts, str):
            texts = [texts]

        for index, text in enumerate(texts):
            if not isinstance(text, str):
                raise ValueError("Input text at index {index} must be a string.")

            if len(text.strip()) == 0:
                raise ValueError("Input text at index {index} must not be empty.")
