# ruff: noqa: E402 // ignore import not at top of file

from dotenv import load_dotenv

load_dotenv()

# regular imports from here on
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    evaluation: bool = Field(
        default=False,
        validation_alias=AliasChoices("e", "eval"),
        description="Run an evaluation instead of the frontend",
    )

    model_config = SettingsConfigDict(env_prefix="PEA_", cli_parse_args=True)


def run_frontend() -> None:
    from gradio.blocks import Blocks

    from privacy_enabled_agents.frontend.gradio import create_gradio_interface

    demo: Blocks = create_gradio_interface()
    demo.launch(server_name="localhost")


def main() -> None:
    settings: Settings = Settings()

    if settings.evaluation:
        pass
        # TODO: add eval options here

    else:
        run_frontend()


if __name__ == "__main__":
    main()
