from typing import Optional, Union

from gliner import GLiNER

from src.data_models import DetectionResult

MODEL: str = "urchade/gliner_multi_pii-v1"  # Link: https://huggingface.co/urchade/gliner_multi_pii-v1
DEFAULT_ENTITIES: list[str] = ["person", "email", "phone number", "adress", "iban", "credit card number", "location"]

gliner_pii: GLiNER = GLiNER.from_pretrained(MODEL)


def detect_pii(texts: Union[str, list[str]], entity_labels: Optional[list[str]] = None, threshold: int = 0.5) -> list[DetectionResult]:
    if isinstance(texts, str):
        texts = [texts]

    if entity_labels is None:
        entity_labels = DEFAULT_ENTITIES

    predictions_per_text = gliner_pii.batch_predict_entities(texts=texts, labels=entity_labels, threshold=threshold)

    detection_results: list[DetectionResult] = []

    for predictions, text in zip(predictions_per_text, texts):
        detection_results.append(DetectionResult.model_validate({"entities": predictions, "text": text, "threshold": threshold}))

    return detection_results
