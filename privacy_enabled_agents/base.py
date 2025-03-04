from pydantic import BaseModel, Field


class Entity(BaseModel):
    start: int
    end: int
    text: str
    label: str
    score: float = Field(ge=0.0, le=1.0)
