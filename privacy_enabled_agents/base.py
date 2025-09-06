from typing import Self

from langchain_core.messages import BaseMessage
from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic
from pydantic import AliasChoices, BaseModel, Field, FilePath, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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


class PEASettings(BaseSettings):
    evaluation: FilePath | None = Field(
        default=None,
        validation_alias=AliasChoices("e", "eval"),
        description="Path to the evaluation config file. Needs to be a YAML file.",
    )
    redis_url: str = Field(
        default="redis://localhost:6380",
        validation_alias="redis-url",
        description="URL of the Redis server.",
    )
    valkey_host: str = Field(
        default="localhost",
        validation_alias="valkey-host",
        description="Host of the Valkey server.",
    )
    valkey_port: int = Field(
        default=6379,
        validation_alias="valkey-port",
        description="Port of the Valkey server.",
    )
    gliner_api_url: str = Field(
        default="http://localhost:8081",
        validation_alias="gliner-api-url",
        description="URL of the Gliner API server.",
    )
    poll_link: str | None = Field(
        default=None,
        validation_alias="poll-link",
        description="Link to the poll for feedback.",
    )

    @model_validator(mode="after")
    def validate_eval_config(self) -> Self:
        if not self.evaluation:
            return self

        if not str(self.evaluation).lower().endswith(".yaml"):
            raise ValueError("'evaluation' argument must be a YAML file.")

        return self

    model_config = SettingsConfigDict(env_prefix="PEA_", cli_parse_args=True)
