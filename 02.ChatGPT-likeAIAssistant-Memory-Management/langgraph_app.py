from langchain_ollama import ChatOllama
from langgraph.graph.message import add_messages
from typing import Annotated, Sequence, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage

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


