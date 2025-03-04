from typing import Union

from gliner import GLiNER

from privacy_enabled_agents.detection.base import BaseDetector, DetectionResult


class GlinerPIIDetector(BaseDetector):
    """
    GlinerPIIDetector class for detecting PII entities in text using the GLiNER architecture.

    Model: urchade/gliner_multi_pii-v1
    Link: https://huggingface.co/urchade/gliner_multi_pii-v1
    """

    model: str = "urchade/gliner_multi_pii-v1"
    supported_entities: list[str] = ["person", "email", "phone number", "adress", "iban", "credit card number", "location"]

    def __init__(self) -> None:
        super().__init__(supported_entities=self.supported_entities)
        self.gliner = GLiNER.from_pretrained(self.model)

    def detect(self, texts: Union[str, list[str]], threshold: float = 0.5) -> list[DetectionResult]:
        """
        Detect PII entities in the given texts.

        Args:
            texts (Union[str, list[str]]): Texts to detect PII entities in.
            threshold (float): Threshold for the model to consider an entity as a PII entity.

        Returns:
            list[DetectionResult]: List of DetectionResult objects containing the detected entities.
        """
        self.validate_input(texts)

        if isinstance(texts, str):
            texts = [texts]

        predictions_per_text = self.gliner.batch_predict_entities(texts=texts, labels=self.supported_entities, threshold=threshold)

        detection_results: list[DetectionResult] = []

        for predictions, text in zip(predictions_per_text, texts):
            detection_results.append(DetectionResult.model_validate({"entities": predictions, "text": text, "threshold": threshold}))

        return detection_results


class GlinerMedicalDetector(BaseDetector):
    """
    GlinerMedicalDetector class for detecting medical entities in text using the GLiNER architecture.

    Model: urchade/gliner_large_bio-v0.1
    Link: https://huggingface.co/urchade/gliner_large_bio-v0.1
    """

    model = "urchade/gliner_large_bio-v0.1"
    supported_entities = [
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
        super().__init__(supported_entities=self.supported_entities)
        self.gliner = GLiNER.from_pretrained(self.model)

    def detect(self, texts: Union[str, list[str]], threshold: float = 0.3) -> list[DetectionResult]:
        """
        Detect medical entities in the given texts.

        Args:
            texts (Union[str, list[str]]): Texts to detect medical entities in.
            threshold (float): Threshold for the model to consider an entity as a medical entity.

        Returns:
            list[DetectionResult]: List of DetectionResult objects containing the detected entities.
        """
        self.validate_input(texts)

        if isinstance(texts, str):
            texts = [texts]

        predictions_per_text = self.gliner.batch_predict_entities(texts=texts, labels=self.supported_entities, threshold=threshold)

        detection_results: list[DetectionResult] = []

        for predictions, text in zip(predictions_per_text, texts):
            detection_results.append(DetectionResult.model_validate({"entities": predictions, "text": text, "threshold": threshold}))

        return detection_results
