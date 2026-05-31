import chainlit as cl
from langchain_ollama import ChatOllama
from langgraph.graph.message import add_messages
from typing import Annotated, Sequence, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

import os
from chainlit.types import ThreadDict
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

from dotenv import load_dotenv
load_dotenv(override=True)


#LLM
llm = ChatOllama(
    model="qwen2.5",
    temperature=0.5,
)

#Agent State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

#Node
async def assistant(state: AgentState):
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}

#Graph Builder
graph_builder = StateGraph(AgentState)
graph_builder.add_node("assistant", assistant)
graph_builder.add_edge(START, "assistant")
graph_builder.add_edge("assistant", END)

graph = graph_builder.compile()


#Chainlit
#ChatStart
@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("state", {"messages": []})
    await cl.Message("👋 Hello! AI Assistant ready.").send()

#OnMessage
@cl.on_message
async def on_message(msg: cl.Message):

    state = cl.user_session.get("state")
    state["messages"].append(HumanMessage(content=msg.content))

    msg_out = cl.Message(content="")
    await msg_out.send()

    final_text = ""
    async for chunk in graph.astream(
        {"messages": state["messages"]},
        stream_mode="messages",
        version = 'v2'
    ):
        message_chunk, metadata = chunk['data']

        if message_chunk.content:
            final_text += message_chunk.content
            await msg_out.stream_token(message_chunk.content)

    msg_out.content = final_text
    await msg_out.update()

    state["messages"].append(AIMessage(content=final_text))
    cl.user_session.set("state", state)
    # print("\n\n STATE: ", state, "\n")

# Authentication
@cl.password_auth_callback
def auth_callback(username: str, password: str):
    if username == "admin" and password == "admin":
        return cl.User(identifier="admin", metadata={"role": "admin"})
    return None

# Data Layer
@cl.data_layer
def get_data_layer():
    conninfo = os.getenv("DATABASE_URL")
    
    if not conninfo:
        print("\nDATABASE_URL not found in environment variables.")
        return None

    try:
        data_layer = SQLAlchemyDataLayer(conninfo=conninfo)
        return data_layer
    except Exception as e:
        print(f"\n\nFailed to initialize SQLAlchemyDataLayer: {e}")
        return None
    
# Resume chat with proper message loading
@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    try:
        steps = thread.get("steps", [])
        # print("\n\nSTEPS", steps)
        messages = []
        for step in steps:
            step_type = step.get("type")
            content = (step.get("output") or "").strip()
            if not content:
                continue  # skip empty rows
        
            if step_type == "user_message":
                messages.append(HumanMessage(content=content))
            elif step_type == "assistant_message":
                messages.append(AIMessage(content=content))
        cl.user_session.set("state", {"messages": messages})
        print("\n\nMESSAGES: ", messages)
    except Exception as e:
    
        print(f"\nError resuming chat: {e}")
        cl.user_session.set("state", {"messages": []})
