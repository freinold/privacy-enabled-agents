from abc import ABC, abstractmethod
from typing import Optional, Sequence, Union

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from privacy_enabled_agents.base import Entity


class DetectionResult(BaseModel, Runnable):
    entities: list[Entity]
    text: str
    threshold: Optional[float] = Field(ge=0.0, le=1.0, default=None)


class DetectionValidationException(Exception):
    """Exception raised when the input text is invalid."""


class BaseDetector(ABC):
    """
    Abstract base class for implementing various detection techniques on different categories of data.

    Provides a common interface for all detection techniques.
    """

    _supported_entities: list[str]

    def __init__(self) -> None:
        pass

    @abstractmethod
    def get_supported_entities(self) -> list[str]:
        """
        Returns the list of entities supported by this detector.

        Returns:
            list[str]: The list of supported entities.
        """
        return self._supported_entities

    @abstractmethod
    def invoke(self, text: str, threshold: Optional[float] = None) -> DetectionResult:
        """
        Detects entities in the given text.

        Args:
            text (str): The text to be analyzed.
            threshold (Optional[float]): The threshold for the detection process. Not all detectors may use this parameter.

        Returns:
            DetectionResult: A list of DetectionResults containing the detected entities.
        """
        pass

    @abstractmethod
    def batch(self, texts: Sequence[str], threshold: Optional[float] = None) -> list[DetectionResult]:
        """
        Detects entities in a batch of texts.

        Args:
            texts (Sequence[str]): The texts to be analyzed.
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
            DetectionValidationException: If the input text is invalid.
        """
        if isinstance(texts, str):
            texts = [texts]

        for index, text in enumerate(texts):
            if not isinstance(text, str):
                raise ValueError("Input text at index {index} must be a string.")

            if len(text.strip()) == 0:
                raise ValueError("Input text at index {index} must not be empty.")
