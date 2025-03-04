# ruff: noqa: E402 (no import at top level) suppressed on this file as we need to inject the truststore before importing the other modules

from dotenv import load_dotenv
from truststore import inject_into_ssl

dotenv_loaded = load_dotenv()
inject_into_ssl()

from datetime import datetime
from typing import Annotated
from uuid import uuid4

from langchain.tools import BaseTool
from langchain_community.tools import SearxSearchResults
from langchain_community.utilities import SearxSearchWrapper
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


# Create tools
search = SearxSearchWrapper(engines=["bing"])

websearch_tool = SearxSearchResults(
    name="websearch",
    num_results=5,
    description="Search for general information on the web",
    wrapper=search,
)


class CurrentDate(BaseTool):
    name: str = "current_date"
    description: str = "A tool that returns the current date and time in ISO format."

    def _run(self) -> str:
        return datetime.now().isoformat()


date_tool = CurrentDate()

tools = [
    websearch_tool,
    date_tool,
]

# Create chat model and bind tools
chat_model = ChatOpenAI(model="gpt-4o")
chat_model_with_tools = chat_model.bind_tools(
    tools, parallel_tool_calls=False
)  # Disable parallel tool calls to ensure that the tools are called in the order they are defined

# Create a graph builder
graph_builder = StateGraph(State)

# Create tool node
tool_node = ToolNode(tools)


# Create chatbot node
def chatbot_with_tools(state: State):
    return {"messages": [chat_model_with_tools.invoke(state["messages"])]}


# Add nodes to the graph
graph_builder.add_node("chatbot", chatbot_with_tools)
graph_builder.add_node("tools", tool_node)

# Add edges to the graph
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.set_entry_point("chatbot")

# Create a callback handler for tracing
langfuse_handler = CallbackHandler(trace_name="Websearch Agent")

# Setup memory saver
memory_saver = MemorySaver()

# Compile the graph
graph = graph_builder.compile(checkpointer=memory_saver).with_config({"callbacks": [langfuse_handler]})


img = graph.get_graph().draw_mermaid_png()
with open("img/websearch_agent.png", "wb") as f:
    f.write(img)


thread_id = uuid4()


def stream_graph_updates(user_input: str):
    input_message = HumanMessage(content=user_input)
    input_message.pretty_print()
    for event in graph.stream(input={"messages": [input_message]}, config={"configurable": {"thread_id": thread_id}}):
        for value in event.values():
            for message in value["messages"]:
                if isinstance(message, BaseMessage):
                    message.pretty_print()


def run_agent() -> None:
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)


if __name__ == "__main__":
    run_agent()
