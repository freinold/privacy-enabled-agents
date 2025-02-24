# ruff: noqa: E402 (no import at top level) suppressed on this file as we need to inject the truststore before importing the other modules

from dotenv import load_dotenv
from truststore import inject_into_ssl

dotenv_loaded = load_dotenv()
inject_into_ssl()

from typing import Annotated

from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)


langfuse_handler = CallbackHandler(trace_name="Basic Agent")


chat_model = ChatOpenAI(model="gpt-4o")


def _chatbot(state: State):
    return {"messages": [chat_model.invoke(state["messages"])]}


graph_builder.add_node("chatbot", _chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile().with_config({"callbacks": [langfuse_handler]})

# Save the graph as an image
img = graph.get_graph().draw_mermaid_png()
with open("basic_agent.png", "wb") as f:
    f.write(img)


def _stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [HumanMessage(content=user_input)]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)


def run_agent() -> None:
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        _stream_graph_updates(user_input)
