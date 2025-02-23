from typing import Optional, Union

from gliner import GLiNER

from src.data_models import DetectionResult

MODEL: str = "urchade/gliner_large_bio-v0.1" # Link: https://huggingface.co/urchade/gliner_large_bio-v0.1
DEFAULT_ENTITIES: list[str] = ["Disease", "Illness", "Anatomy", "Symptom", "Treatment", "Test", "Drug", "Procedure", "Virus", "Bacteria", "Medical Worker", "Doctor"]

gliner_medical: GLiNER = GLiNER.from_pretrained(MODEL, local_files_only=False)

def detect_medical(texts: Union[str, list[str]], entity_labels: Optional[list[str]] = None, threshold: int = 0.3) -> list[DetectionResult]:
    if isinstance(texts, str):
        texts = [texts]

    if entity_labels is None:
        entity_labels = DEFAULT_ENTITIES

    predictions_per_text = gliner_medical.batch_predict_entities(texts=texts, labels=entity_labels, threshold=threshold)

    detection_results: list[DetectionResult] = []

    for predictions, text in zip(predictions_per_text, texts):
        detection_results.append(DetectionResult.model_validate({"entities": predictions, "text": text, "threshold": threshold}))
        
    return detection_results
