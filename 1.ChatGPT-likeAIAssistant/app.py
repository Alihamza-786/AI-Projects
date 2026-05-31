import chainlit as cl
from langchain_ollama import ChatOllama
from langgraph.graph.message import add_messages
from typing import Annotated, Sequence, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


llm = ChatOllama(
    model="qwen2.5",
    temperature=0.5,
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


async def assistant(state: AgentState):
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


graph_builder = StateGraph(AgentState)
graph_builder.add_node("assistant", assistant)
graph_builder.add_edge(START, "assistant")
graph_builder.add_edge("assistant", END)

graph = graph_builder.compile()


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("state", {"messages": []})
    await cl.Message("👋 Hello! AI Assistant ready.").send()


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

    state["messages"].append(AIMessage(content=final_text))
    cl.user_session.set("state", state)
    print("\n\n STATE: ", state, "\n")