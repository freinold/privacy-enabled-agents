# ruff: noqa: E402 // ignore import not at top of file

from dotenv import load_dotenv

load_dotenv()

from gradio.blocks import Blocks

from privacy_enabled_agents.frontend.gradio import create_gradio_interface

demo: Blocks = create_gradio_interface()
demo.launch(server_name="localhost")
