from typing import Sequence

from gliner import GLiNER

from privacy_enabled_agents.detection.base import BaseDetector, DetectionResult


class GlinerPIIDetector(BaseDetector):
    """
    GlinerPIIDetector class for detecting PII entities in text using the GLiNER architecture.

    Model: urchade/gliner_multi_pii-v1
    Link: https://huggingface.co/urchade/gliner_multi_pii-v1
    """

    _model: str = "urchade/gliner_multi_pii-v1"
    _supported_entities: list[str] = ["person", "email", "phone number", "adress", "iban", "credit card number", "location"]

    def __init__(self) -> None:
        self._gliner = GLiNER.from_pretrained(self._model)

    def invoke(self, text: str, threshold: float = 0.5) -> DetectionResult:
        """
        Detect PII entities in the given text.

        Args:
            text (str): Text to detect PII entities in.
            threshold (float): Threshold for the model to consider an entity as a PII entity. Defaults to 0.5.

        Returns:
            DetectionResult: DetectionResult object containing the detected entities.

        Raises:
            DetectionValidationError: If the text is not of type str or its length is 0.
        """
        self.validate_input(text)
        entities = self._gliner.predict_entities(text=text, labels=self._supported_entities, threshold=threshold)
        detection_result = DetectionResult.model_validate({"entities": entities, "text": text, "threshold": threshold})
        return detection_result

    def batch(self, texts: Sequence[str], threshold: float = 0.5) -> list[DetectionResult]:
        """
        Detect PII entities in the given texts.

        Args:
            texts (Sequence[str]): List of texts to detect PII entities in.
            threshold (float): Threshold for the model to consider an entity as a PII entity. Defaults to 0.5.

        Returns:
            list[DetectionResult]: List of DetectionResult objects containing the detected entities.

        Raises:
            DetectionValidationError: If any the texts are not of type str or their length is 0.
        """
        self.validate_input(texts)
        batch_entities = self._gliner.batch_predict_entities(texts=texts, labels=self._supported_entities, threshold=threshold)
        detection_results: list[DetectionResult] = []
        for entities, text in zip(batch_entities, texts):
            detection_results.append(DetectionResult.model_validate({"entities": entities, "text": text, "threshold": threshold}))
        return detection_results


class GlinerMedicalDetector(BaseDetector):
    """
    GlinerMedicalDetector class for detecting medical entities in text using the GLiNER architecture.

    Model: urchade/gliner_large_bio-v0.1
    Link: https://huggingface.co/urchade/gliner_large_bio-v0.1
    """

    _model: str = "urchade/gliner_large_bio-v0.1"
    _supported_entities: list[str] = [
        "Disease",
        "Illness",
        "Anatomy",
        "Symptom",
        "Treatment",
        "Test",
        "Drug",
        "Procedure",
        "Virus",
        "Bacteria",
        "Medical Worker",
        "Doctor",
    ]

    def __init__(self) -> None:
        super().__init__(supported_entities=self._supported_entities)
        self._gliner = GLiNER.from_pretrained(self._model)

    def invoke(self, text: str, threshold: float = 0.5) -> DetectionResult:
        """
        Detect medical entities in the given text.

        Args:
            text (str): Text to detect PII entities in.
            threshold (float): Threshold for the model to consider an entity as a PII entity. Defaults to 0.5.

        Returns:
            DetectionResult: DetectionResult object containing the detected entities.

        Raises:
            DetectionValidationError: If the text is not of type str or its length is 0.
        """
        self.validate_input(text)
        entities = self._gliner.predict_entities(text=text, labels=self._supported_entities, threshold=threshold)
        detection_result = DetectionResult.model_validate({"entities": entities, "text": text, "threshold": threshold})
        return detection_result

    def batch(self, texts: Sequence[str], threshold: float = 0.5) -> list[DetectionResult]:
        """
        Detect medical entities in the given texts.

        Args:
            texts (Sequence[str]): List of texts to detect PII entities in.
            threshold (float): Threshold for the model to consider an entity as a PII entity. Defaults to 0.5.

        Returns:
            list[DetectionResult]: List of DetectionResult objects containing the detected entities.

        Raises:
            DetectionValidationError: If any the texts are not of type str or their length is 0.
        """
        self.validate_input(texts)
        batch_entities = self._gliner.batch_predict_entities(texts=texts, labels=self._supported_entities, threshold=threshold)
        detection_results: list[DetectionResult] = []
        for entities, text in zip(batch_entities, texts):
            detection_results.append(DetectionResult.model_validate({"entities": entities, "text": text, "threshold": threshold}))
        return detection_results
