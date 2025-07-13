# ruff: noqa: E402 (no import at top level) suppressed on this file as we need to inject the truststore before importing the other modules

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from truststore import inject_into_ssl

dotenv_loaded = load_dotenv()
inject_into_ssl()

# End of special imports

import logging.config

from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.redis import RedisSaver
from langgraph.prebuilt import create_react_agent
from yaml import safe_load

from privacy_enabled_agents.chat_models.privacy_wrapper import PrivacyEnabledChatModel
from privacy_enabled_agents.detection.remote_gliner import RemoteGlinerDetector
from privacy_enabled_agents.replacement.placeholder import PlaceholderReplacer
from privacy_enabled_agents.storage.valkey import ValkeyStorage

with open("logconf.yaml", "r", encoding="utf-8") as file:
    log_config = safe_load(file)

logging.config.dictConfig(log_config)

langfuse_handler = CallbackHandler()

chat_model = ChatOpenAI(model="gpt-4o")
detector = RemoteGlinerDetector(base_url="http://localhost:8081")
storage = ValkeyStorage()
replacer = PlaceholderReplacer(storage=storage)
privacy_chat_model = PrivacyEnabledChatModel(model=chat_model, replacer=replacer, detector=detector)

with RedisSaver.from_conn_string("redis://localhost:6380") as checkpointer:
    checkpointer.setup()

    graph = create_react_agent(
        model=privacy_chat_model,
        tools=[],
        prompt="You are a helpful assistant.",
        checkpointer=checkpointer,
    ).with_config(RunnableConfig(callbacks=[langfuse_handler]))

# Save the graph as an image
img = graph.get_graph().draw_mermaid_png()
with open("img/basic_agent.png", "wb") as f:
    f.write(img)


def _stream_graph_updates(user_input: str):
    for event in graph.stream(
        {"messages": [HumanMessage(content=user_input)]}, config={"configurable": {"thread_id": privacy_chat_model.context_id}}
    ):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)


def run_agent() -> None:
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q", "bye"]:
            print("Goodbye!")
            break

        _stream_graph_updates(user_input)


if __name__ == "__main__":
    run_agent()
