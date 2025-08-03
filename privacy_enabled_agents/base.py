from pydantic import AliasChoices, BaseModel, Field

PII_PRELUDE_PROMPT: str = """
<Prelude>
You are a helpful assistant with privacy protection capabilities.

When you receive a user query, it can include obstructed personal information (PII) you can't see, such as names, addresses, or other sensitive data.
Your task is to assist the user while ensuring that any PII is not exposed in your responses.

Use the provided tools like always, passing the obstructed PII if needed.
The user will see the full information, don't worry about that.
</Prelude>
"""


class Entity(BaseModel):
    start: int
    end: int
    text: str
    label: str = Field(validation_alias=AliasChoices("label", "type"))
    score: float = Field(ge=0.0, le=1.0)


class UnsupportedEntityException(Exception):
    """Exception raised when an unsupported entity is encountered."""

    def __init__(self, entity: str):
        super().__init__(f"Unsupported entity: {entity}")
        self.entity = entity
