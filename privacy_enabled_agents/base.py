from pydantic import BaseModel, Field


class Entity(BaseModel):
    start: int
    end: int
    text: str
    label: str
    score: float = Field(ge=0.0, le=1.0)


class UnsupportedEntityException(Exception):
    """Exception raised when an unsupported entity is encountered."""

    def __init__(self, entity: str):
        super().__init__(f"Unsupported entity: {entity}")
        self.entity = entity
