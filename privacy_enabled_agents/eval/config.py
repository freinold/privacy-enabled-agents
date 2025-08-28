"""Evaluation configuration for the privacy-enabled agent."""

from typing import Literal

from pydantic import BaseModel, Field

from privacy_enabled_agents.runtime import PrivacyAgentConfig


class EvalConfig(BaseModel):
    """Evaluation configuration for the privacy-enabled agent."""

    agent_config: PrivacyAgentConfig = Field(
        default_factory=PrivacyAgentConfig,
        description="Configuration for the privacy agent.",
    )
    eval_runs: int = Field(
        default=10,
        description="Number of evaluation runs to perform.",
    )
    user_model_provider: Literal["openai", "mistral"] = Field(
        default="mistral",
        description="Provider of the model representing the user.",
    )
    user_model_name: str = Field(
        default="mistral-large-2508",
        description="Name of the model representing the user.",
    )
    max_turns: int = Field(
        default=10,
        description="Maximum number of conversation turns before forcing completion.",
    )
    enable_baseline_comparison: bool = Field(
        default=False,
        description="Whether to run the non-privacy baseline agent for comparison with the privacy-enabled agent.",
    )
