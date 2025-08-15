from langchain_core.messages import BaseMessage
from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic
from pydantic import AliasChoices, BaseModel, Field

PII_PRELUDE_PROMPT = """
<Prelude>
You are a helpful assistant with privacy protection capabilities.

When you receive a user query, it can include obstructed personal information (PII) you can't see, such as names, addresses, or other sensitive data.
Your task is to assist the user while ensuring that any PII is not exposed in your responses.

Use the provided tools like always, passing the obstructed PII if needed.
The user will see the full information, don't worry about that.
</Prelude>
"""

BASE_ENTITIES: set[str] = {
    "name",
    "location",
    "organization",
    "address",
    "email",
    "phone",
}


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


class PrivacyEnabledAgentState(AgentStatePydantic):
    """State for the basic agent with privacy features."""

    privacy_protected_messages: list[BaseMessage] = Field(
        default_factory=list, description="Messages with PII/PHI replaced - what the LLM actually is given"
    )
