from pydantic import BaseModel, Field


class Entity(BaseModel):
    start: int
    end: int
    text: str
    label: str
    score: float = Field(ge=0.0, le=1.0)


class DetectionResult(BaseModel):
    entities: list[Entity]
    text: str
    threshold: float
