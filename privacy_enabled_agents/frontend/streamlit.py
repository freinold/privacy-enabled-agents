from uuid import uuid4

import streamlit as st
from langchain_core.messages import HumanMessage

from privacy_enabled_agents.agents.basic_agent import graph

st.title("Basic Agent")

if "graph" not in st.session_state:
    st.session_state.graph = graph

if "chat_id" not in st.session_state:
    chat_id = str(uuid4())
    st.session_state.chat_id = chat_id

for message in st.session_state.graph.get_state(
    config={
        "configurable": {
            "thread_id": st.session_state.chat_id,
        }
    }
).values.get("messages", []):
    with st.chat_message(message.type):
        st.write(message.content)

if input_text := st.chat_input("Type your message here..."):
    with st.chat_message("user"):
        st.write(input_text)

    with st.chat_message("assistant"):
        output = st.session_state.graph.invoke(
            input={"messages": [HumanMessage(content=input_text)]},
            config={
                "configurable": {
                    "thread_id": st.session_state.chat_id,
                }
            },
        )
        response = st.write(output["messages"][-1].content)
