from typing import Any, Literal, Optional, Sequence, Union

from gliner import GLiNER
from langchain_core.runnables import RunnableConfig
from pydantic import Field, TypeAdapter

from privacy_enabled_agents.detection.base import BaseDetector, DetectorInput, DetectorOutput


class GlinerPIIDetector(BaseDetector):
    """
    GlinerPIIDetector class for detecting PII entities in text using the GLiNER architecture.

    - Model: E3-JSI/gliner-multi-pii-domains-v1
    - Link: https://huggingface.co/E3-JSI/gliner-multi-pii-domains-v1
    """

    model: str = "E3-JSI/gliner-multi-pii-domains-v1"
    supported_entities: set[str] | Literal["ANY"] = {
        "person",
        "email",
        "phone number",
        "address",
        "iban",
        "credit card number",
        "location",
        "age",
        "date",
        "country",
        "state",
        "city",
        "zip code",
    }
    threshold: float = Field(default=0.5, le=1.0, ge=0.0, description="Threshold for entity detection confidence.")

    def __init__(self) -> None:
        super().__init__()
        self._gliner: GLiNER = GLiNER.from_pretrained(self.model)

    def invoke(
        self,
        input: DetectorInput,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> DetectorOutput:
        # Validate the input
        self.validate_text(input)

        # Predict the entities
        entities = self._gliner.predict_entities(
            text=input,
            labels=self.supported_entities,
            threshold=self.threshold,
        )

        # Validate the output
        type_adapter = TypeAdapter(DetectorOutput)
        output: DetectorOutput = type_adapter.validate_python(entities)
        return output

    def batch(
        self,
        inputs: Sequence[DetectorInput],
        config: Union[RunnableConfig, list[RunnableConfig], None] = None,
        **kwargs: Any,
    ) -> list[DetectorOutput]:
        # Validate the input
        for input in inputs:
            self.validate_text(input)

        # Detect entities in the batch of texts
        batch_entities = self._gliner.batch_predict_entities(
            texts=list(inputs),
            labels=self.supported_entities,
            threshold=self.threshold,
        )

        # Validate the output
        type_adapter = TypeAdapter(list[DetectorOutput])
        outputs: list[DetectorOutput] = type_adapter.validate_python(batch_entities)
        return outputs


class GlinerMedicalDetector(BaseDetector):
    """
    GlinerMedicalDetector class for detecting medical entities in text using the GLiNER architecture.

    - Model: Ihor/gliner-biomed-large-v1.0
    - Link: https://huggingface.co/Ihor/gliner-biomed-large-v1.0
    """

    model: str = "Ihor/gliner-biomed-large-v1.0"
    supported_entities: set[str] | Literal["ANY"] = {
        "Anatomy",
        "Bacteria",
        "Demographic information",
        "Disease",
        "Doctor",
        "Drug dosage",
        "Drug frequency",
        "Drug",
        "Illness",
        "Lab test value",
        "Lab test",
        "Medical Worker",
        "Procedure",
        "Symptom",
        "Test",
        "Treatment",
        "Virus",
    }
    threshold: float = Field(default=0.3, le=1.0, ge=0.0, description="Threshold for entity detection confidence.")

    def __init__(self) -> None:
        super().__init__()
        self._gliner: GLiNER = GLiNER.from_pretrained(self.model)

    def invoke(
        self,
        input: DetectorInput,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> DetectorOutput:
        # Validate the input
        self.validate_text(input)

        # Predict the entities
        entities = self._gliner.predict_entities(text=input, labels=self.supported_entities, threshold=self.threshold)

        # Validate the output
        type_adapter = TypeAdapter(DetectorOutput)
        output: DetectorOutput = type_adapter.validate_python(entities)
        return output

    def batch(
        self,
        inputs: Sequence[DetectorInput],
        config: RunnableConfig | list[RunnableConfig] | None = None,
        **kwargs: Any,
    ) -> list[DetectorOutput]:
        # Validate the input
        for input in inputs:
            self.validate_text(input)

        # Detect entities in the batch of texts
        batch_entities = self._gliner.batch_predict_entities(
            texts=list(inputs),
            labels=self.supported_entities,
            threshold=self.threshold,
        )

        # Validate the output
        type_adapter = TypeAdapter(list[DetectorOutput])
        outputs: list[DetectorOutput] = type_adapter.validate_python(batch_entities)
        return outputs
