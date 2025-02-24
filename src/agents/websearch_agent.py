# ruff: noqa: E402 (no import at top level) suppressed on this file as we need to inject the truststore before importing the other modules

from dotenv import load_dotenv
from truststore import inject_into_ssl

dotenv_loaded = load_dotenv()
inject_into_ssl()

from datetime import datetime
from typing import Annotated

from langchain.tools import BaseTool
from langchain_community.tools import SearxSearchResults
from langchain_community.utilities import SearxSearchWrapper
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.system import SystemMessage
from langchain_core.messages.tool import ToolMessage
from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages] = [
        SystemMessage(
            """
            Du bist ein Websearch Agent.
            Du kannst zur Beantwortung von Fragen im Web auf bestimmten Seiten suchen, indem du Tools benutzt.
            Wenn du zu einer Frage oder Aufgabe keine Informationen hast, gib einfach "Ich weiß es nicht" an.
            """
        )
    ]


# Create tools
search = SearxSearchWrapper()
muenchen_tool = SearxSearchResults(
    name="muenchen_de-search",
    num_results=3,
    description="Search for general Munich related information on muenchen.de",
    wrapper=search,
    kwargs={"engines": ["google", "bing"], "query_suffix": "site:muenchen.de"},
)

tourismus_tool = SearxSearchResults(
    name="muenchen_travel-search",
    num_results=3,
    description="Search for Munich tourism information on muenchen.travel",
    wrapper=search,
    kwargs={"engines": ["google", "bing"], "query_suffix": "site:muenchen.travel"},
)


class CurrentDate(BaseTool):
    name: str = "current_date"
    description: str = "A tool that returns the current date and time in ISO format."

    def _run(self) -> str:
        return datetime.now().isoformat()


class BookTrip(BaseTool):
    name: str = "book_trip"
    description: str = "A tool that books a trip to Munich."

    def _run(self) -> str:
        return "Trip booked to Munich!"


date_tool = CurrentDate()

tools = [
    muenchen_tool,
    tourismus_tool,
    date_tool,
]

# Create chat model and bind tools
chat_model = ChatOpenAI(model="gpt-4o")
chat_model_with_tools = chat_model.bind_tools(tools)

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

# Compile the graph
graph = graph_builder.compile().with_config({"callbacks": [langfuse_handler]})


img = graph.get_graph().draw_mermaid_png()
with open("img/websearch_agent.png", "wb") as f:
    f.write(img)


def stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [HumanMessage(content=user_input)]}):
        for value in event.values():
            for message in value["messages"]:
                if isinstance(message, AIMessage):
                    if message.content:
                        print(f"Agent: {message.content}")
                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            print(f"Agent: {tool_call['name']} tool called.")
                elif isinstance(message, ToolMessage):
                    print(f"Tool: {message.content}")


def run_agent() -> None:
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)
