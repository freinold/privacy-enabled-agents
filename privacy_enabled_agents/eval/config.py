from pathlib import Path
from typing import Literal, Self

from pydantic import Field, FilePath, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from privacy_enabled_agents.runtime import PrivacyAgentConfig


class EvalConfig(BaseSettings):
    agent_config: PrivacyAgentConfig = Field(
        default_factory=PrivacyAgentConfig,
        description="Configuration for the privacy agent.",
    )
    eval_dataset: FilePath = Field(
        default=Path("eval_dataset.csv"),
        description="Path to the evaluation dataset.",
    )
    eval_sample: int | None = Field(
        default=None,
        description="Number of samples to evaluate on. If None, evaluates on the entire dataset.",
    )
    user_model_provider: Literal["openai", "mistral"] = Field(
        default="mistral",
        description="Provider of the model representing the user.",
    )
    user_model_name: str = Field(
        default="mistral-large-2508",
        description="Name of the model representing the user.",
    )

    @model_validator(mode="after")
    def validate_eval_dataset(self) -> Self:
        if not str(self.eval_dataset).lower().endswith(".csv"):
            raise ValueError("eval_dataset must be a CSV file.")
        else:
            return self

    model_config = SettingsConfigDict(
        json_file="eval_config.json",
        json_file_encoding="utf-8",
        yaml_file="eval_config.yaml",
        yaml_file_encoding="utf-8",
    )
