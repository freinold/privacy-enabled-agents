# ruff: noqa: E402 // ignore import not at top of file
from dotenv import load_dotenv

load_dotenv()

from privacy_enabled_agents import PEASettings


def run_frontend() -> None:
    from gradio.blocks import Blocks

    from privacy_enabled_agents.frontend.gradio import create_gradio_interface

    demo: Blocks = create_gradio_interface()
    demo.launch(server_name="localhost", server_port=8080)


def main() -> None:
    settings: PEASettings = PEASettings()

    if settings.evaluation is not None:
        from privacy_enabled_agents.eval.runner import run_evaluation

        run_evaluation(settings.evaluation)
    else:
        run_frontend()


if __name__ == "__main__":
    main()
