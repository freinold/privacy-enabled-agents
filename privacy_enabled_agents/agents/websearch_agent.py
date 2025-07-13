# ruff: noqa: E402 (no import at top level) suppressed on this file as we need to inject the truststore before importing the other modules

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from truststore import inject_into_ssl

dotenv_loaded = load_dotenv()
inject_into_ssl()

# End of special imports

import logging.config

from langchain.schema import HumanMessage
from langchain_community.tools import DuckDuckGoSearchRun
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

search = DuckDuckGoSearchRun()

system_prompt = """
You are a helpful assistant with privacy protection capabilities.

When you receive a user query, it can include obstructed personal information (PII) you can't see, such as names, addresses, or other sensitive data.
Your task is to assist the user while ensuring that any PII is not exposed in your responses.

Use the provided tools like always, passing the obstructed PII if needed.
The user will see the full information, don't worry about that.
"""

with RedisSaver.from_conn_string("redis://localhost:6380") as checkpointer:
    checkpointer.setup()

    graph = create_react_agent(
        model=privacy_chat_model,
        tools=[search],
        prompt=system_prompt,
        checkpointer=checkpointer,
    ).with_config(RunnableConfig(callbacks=[langfuse_handler]))

# Save the graph as an image
img = graph.get_graph().draw_mermaid_png()
with open("img/websearch_agent.png", "wb") as f:
    f.write(img)


def _stream_graph_updates(user_input: str):
    for event in graph.stream(
        {"messages": [HumanMessage(content=user_input)]}, config={"configurable": {"thread_id": privacy_chat_model.context_id}}
    ):
        for value in event.values():
            latest_message: BaseMessage = value["messages"][-1]
            if isinstance(latest_message, AIMessage):
                if len(latest_message.content) > 0:
                    print("🤖 Assistant:", latest_message.content)
                elif len(latest_message.tool_calls) > 0:
                    for tool_call in latest_message.tool_calls:
                        print(f"🔨 Assistant is calling tool: {tool_call.get('name')} with arguments: {tool_call.get('args')}")


def run_agent() -> None:
    while True:
        user_input = input("🧑 User: ")
        if user_input.lower() in ["quit", "exit", "q", "bye"]:
            print("Goodbye!")
            break

        _stream_graph_updates(user_input)


if __name__ == "__main__":
    run_agent()
