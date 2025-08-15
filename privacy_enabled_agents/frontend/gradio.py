from logging import Logger, getLogger

import gradio as gr
import gradio.themes as gr_themes

from privacy_enabled_agents.frontend.helpers import create_chat_function
from privacy_enabled_agents.runtime import create_privacy_agent

# Create logger for this module
logger: Logger = getLogger(__name__)

user_chat_doc = """
**User-facing Conversation**<br/>
This is the conversation from the user's side.<br/>
Messages here contain all PII, like a normal conversation would do.<br/>
Users can chat like they are in other AI chat interfaces.
"""

bot_chat_doc = """
**Bot-facing Conversation**<br/>
This is the 'real' conversation from the bot's side.<br/>
Messages here contain placeholders for PII.<br/>
The AI model has to work with these placeholders for tool calls.
"""

basic_scenario_description = """
### Basic Agent

This is a basic agent with privacy features.

Users can interact with the agent while their personal information is protected.
The agent will respond to queries without exposing any sensitive data.
This agent has no tools or special capabilities.
"""

websearch_scenario_description = """
### Web Search Agent

A helpful and professional web search assistant that finds information online efficiently and accurately.

**Capabilities:**
- Performs web searches using Google
- Provides search results and explanations
- Maintains user privacy during searches
- Handles queries in German region (de-de)

**Privacy Features:**
- User queries are protected with PII placeholders
- Search results are returned securely
"""

medical_scenario_description = """
### Medical Transport Agent

A specialized assistant for healthcare transportation services in München, Germany.

**Capabilities:**
- Book medical transports to/from facilities
- Find nearby medical facilities (hospitals, doctors)
- Check service area coverage
- List and cancel existing transports
- Convert addresses to coordinates

**Required Information:**
- German medical insurance ID
- Patient name and date of birth
- Pickup/destination locations

**Service Area:** München city limits
"""

public_service_scenario_description = """
### Public Service Agent

A professional assistant for city administration's parking permit department.

**Services Available:**
- Check current parking permits
- Apply for new permits (residential, visitor, business)
- Pay permit fees
- Renew existing permits

**Permit Types:**
- Residential permits (€120/year)
- Visitor permits (€50/year)
- Business permits (€300/year)

**Requirements:**
- 30+ days registered residency for eligibility
- One permit per vehicle maximum
"""

financial_scenario_description = """
### Banking Agent

A professional financial assistant and banking advisor for secure banking operations.

**Banking Services:**
- Check account balances
- Transfer money between accounts (IBAN)
- Request credit limit increases
- View transaction history

**Security Features:**
- Full regulatory compliance
- Account ownership verification
- Transaction confirmation details

**Eligibility Requirements:**
- 18+ years for credit limit increases
- 30+ day account history required
- Income-based credit limit calculations
"""


def create_gradio_interface() -> gr.Blocks:
    # Custom CSS with subtle radial gradient background
    css = """
    .gradio-container {
        background: radial-gradient(ellipse at center, #0D9488 0%, #1a2332 70%, #1F2937 100%);
        min-height: 100vh;
    }
    """

    with gr.Blocks(theme=gr_themes.Base(primary_hue="teal"), css=css, fill_width=True) as demo:
        demo.title = "Privacy Enabled Agents"
        gr.Markdown("## Privacy Enabled Agents")

        basic_agent, basic_chat_model = create_privacy_agent(
            "basic",
        )
        basic_chat_fn = create_chat_function("basic", basic_agent, basic_chat_model)

        websearch_agent, websearch_chat_model = create_privacy_agent("websearch", model_provider="openai", model_name="gpt-4.1")
        websearch_chat_fn = create_chat_function("websearch", websearch_agent, websearch_chat_model)

        medical_agent, medical_chat_model = create_privacy_agent("medical")
        medical_chat_fn = create_chat_function("medical", medical_agent, medical_chat_model)

        public_service_agent, public_service_chat_model = create_privacy_agent("public service")
        public_service_chat_fn = create_chat_function("public service", public_service_agent, public_service_chat_model)

        financial_agent, financial_chat_model = create_privacy_agent("financial")
        financial_chat_fn = create_chat_function("financial", financial_agent, financial_chat_model)

        browser_state = gr.BrowserState(storage_key="privacy_agent_session")

        # Load existing session from browser state when page loads
        @demo.load(inputs=[browser_state], outputs=[browser_state])
        def load_existing_session(saved_state):
            if saved_state and saved_state.get("thread_id"):
                logger.info(f"Loading existing session with thread_id: {saved_state['thread_id']}")
                return saved_state
            else:
                # Generate new thread_id for new session
                logger.info("No existing session found, starting a new one.")
                new_state = {}
                return new_state

        with gr.Tab(label="Basic Agent"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Scenario Description\n" + basic_scenario_description)
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=user_chat_doc, container=True)
                        basic_user_chatbot: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/person.png", "resources/robot.png"),
                            height=600,
                        )
                        user_input: gr.Textbox = gr.Textbox(
                            placeholder="Type your message here...",
                            show_label=False,
                            submit_btn=True,
                        )
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=bot_chat_doc, container=True)
                        real_basic_conversation: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/incognito.png", "resources/robot.png"),
                            height=600,
                        )

            user_input.submit(
                fn=basic_chat_fn,
                inputs=[user_input, basic_user_chatbot, browser_state],
                outputs=[basic_user_chatbot, real_basic_conversation, browser_state],
            ).then(
                lambda: "",  # Clear the input after submission
                outputs=[user_input],
            )

        with gr.Tab(label="Websearch Agent"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown(websearch_scenario_description)
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=user_chat_doc, container=True)
                        websearch_user_chatbot: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/person.png", "resources/robot.png"),
                            height=600,
                        )
                        websearch_input: gr.Textbox = gr.Textbox(
                            placeholder="Type your message here...",
                            show_label=False,
                            submit_btn=True,
                        )
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=bot_chat_doc, container=True)
                        real_websearch_conversation: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/incognito.png", "resources/robot.png"),
                            height=600,
                        )

            websearch_input.submit(
                fn=websearch_chat_fn,
                inputs=[websearch_input, websearch_user_chatbot, browser_state],
                outputs=[websearch_user_chatbot, real_websearch_conversation, browser_state],
            ).then(
                lambda: "",  # Clear the input after submission
                outputs=[websearch_input],
            )

        with gr.Tab(label="Medical Agent"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown(medical_scenario_description)
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=user_chat_doc, container=True)
                        medical_user_chatbot: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/person.png", "resources/robot.png"),
                            height=600,
                        )
                        medical_input: gr.Textbox = gr.Textbox(
                            placeholder="Type your message here...",
                            show_label=False,
                            submit_btn=True,
                        )
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=bot_chat_doc, container=True)
                        real_medical_conversation: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/incognito.png", "resources/robot.png"),
                            height=600,
                        )

            medical_input.submit(
                fn=medical_chat_fn,
                inputs=[medical_input, medical_user_chatbot, browser_state],
                outputs=[medical_user_chatbot, real_medical_conversation, browser_state],
            ).then(
                lambda: "",  # Clear the input after submission
                outputs=[medical_input],
            )

        with gr.Tab(label="Public Service Agent"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown(public_service_scenario_description)
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=user_chat_doc, container=True)
                        public_service_user_chatbot: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/person.png", "resources/robot.png"),
                            height=600,
                        )
                        public_service_input: gr.Textbox = gr.Textbox(
                            placeholder="Type your message here...",
                            show_label=False,
                            submit_btn=True,
                        )
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=bot_chat_doc, container=True)
                        real_public_service_conversation: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/incognito.png", "resources/robot.png"),
                            height=600,
                        )

            public_service_input.submit(
                fn=public_service_chat_fn,
                inputs=[public_service_input, public_service_user_chatbot, browser_state],
                outputs=[public_service_user_chatbot, real_public_service_conversation, browser_state],
            ).then(
                lambda: "",  # Clear the input after submission
                outputs=[public_service_input],
            )

        with gr.Tab(label="Financial Agent"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown(financial_scenario_description)
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=user_chat_doc, container=True)
                        financial_user_chatbot: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/person.png", "resources/robot.png"),
                            height=600,
                        )
                        financial_input: gr.Textbox = gr.Textbox(
                            placeholder="Type your message here...",
                            show_label=False,
                            submit_btn=True,
                        )
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.Markdown(value=bot_chat_doc, container=True)
                        real_financial_conversation: gr.Chatbot = gr.Chatbot(
                            type="messages",
                            avatar_images=("resources/incognito.png", "resources/robot.png"),
                            height=600,
                        )

            financial_input.submit(
                fn=financial_chat_fn,
                inputs=[financial_input, financial_user_chatbot, browser_state],
                outputs=[financial_user_chatbot, real_financial_conversation, browser_state],
            ).then(
                lambda: "",  # Clear the input after submission
                outputs=[financial_input],
            )

    return demo
