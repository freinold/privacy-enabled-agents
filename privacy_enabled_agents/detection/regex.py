import re
from typing import Any, Literal

from langchain_core.runnables.config import RunnableConfig

from privacy_enabled_agents import Entity
from privacy_enabled_agents.detection import BaseDetector


class RegexDetector(BaseDetector):
    """
    Detector class for detecting entities in text using regular expressions.
    """

    supported_entities: set[str] | Literal["ANY"] = {
        "email",
        "phone_number",
        "german_medical_insurance_id",
        "credit_card",
        "iban",
    }

    def __init__(self) -> None:
        self._regex_patterns: dict[str, str] = {
            "email": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
            "phone_number": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b|(?:\+[1-9]\d{0,3}[-.\s]?)?(?:\([0-9]{1,4}\)[-.\s]?)?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}",
            "german_medical_insurance_id": r"\b[A-Z]\d{9}\b",
            "credit_card": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
            "iban": r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}\b",
        }

    def invoke(
        self,
        input: str,
        config: RunnableConfig | None = None,
        *,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> list[Entity]:
        entities: list[Entity] = []
        for entity_type, pattern in self._regex_patterns.items():
            for match in re.finditer(pattern, input):
                entities.append(Entity(start=match.start(), end=match.end(), text=match.group(), label=entity_type, score=1.0))
        return entities
