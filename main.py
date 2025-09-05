# ruff: noqa: E402 // ignore import not at top of file

from dotenv import load_dotenv

from privacy_enabled_agents.eval.runner import run_evaluation

load_dotenv()

# regular imports from here on
from typing import Self

from pydantic import AliasChoices, Field, FilePath, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    evaluation: FilePath | None = Field(
        default=None,
        validation_alias=AliasChoices("e", "eval"),
        description="Path to the evaluation config file. Needs to be a YAML file.",
    )

    @model_validator(mode="after")
    def validate_eval_config(self) -> Self:
        if not self.evaluation:
            return self

        if not str(self.evaluation).lower().endswith(".yaml"):
            raise ValueError("'evaluation' argument must be a YAML file.")

        return self

    model_config = SettingsConfigDict(env_prefix="PEA_", cli_parse_args=True)


def run_frontend() -> None:
    from gradio.blocks import Blocks

    from privacy_enabled_agents.frontend.gradio import create_gradio_interface

    demo: Blocks = create_gradio_interface()
    demo.launch(server_name="localhost", server_port=8080)


def main() -> None:
    settings: Settings = Settings()

    if settings.evaluation is not None:
        run_evaluation(settings.evaluation)
    else:
        run_frontend()


if __name__ == "__main__":
    main()
