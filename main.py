# ruff: noqa: E402 // ignore import not at top of file
from dotenv import load_dotenv

load_dotenv()

from logging import Logger, getLogger

from privacy_enabled_agents import PEASettings

logger: Logger = getLogger(__name__)


def run_frontend(server_name: str) -> None:
    from gradio.blocks import Blocks

    from privacy_enabled_agents.frontend.gradio import create_gradio_interface

    demo: Blocks = create_gradio_interface()

    demo.launch(server_name=server_name, server_port=8080)


def main() -> None:
    settings: PEASettings = PEASettings()

    logger.info(f"Starting Privacy-Enabled Agents with settings: {settings.model_dump_json(indent=2)}")

    if settings.evaluation is not None:
        from privacy_enabled_agents.eval.runner import run_evaluation

        run_evaluation(settings.evaluation)
    else:
        server_name: str = "0.0.0.0" if settings.public_frontend else "localhost"
        run_frontend(server_name)


if __name__ == "__main__":
    main()
