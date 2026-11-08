from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from typing import Annotated, Sequence, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.prebuilt import ToolNode
from tools import tools

from prompts import AGENT_PROMPT
from zoneinfo import ZoneInfo
from datetime import datetime



#LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    streaming = True
).bind_tools(tools)

#Agent State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

#Node
async def agent_node(state: AgentState):
    now = datetime.now(ZoneInfo("Asia/Karachi"))
    now_time = f"Time zone: Asia/Karachi, Date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    system_prompt = SystemMessage(
        content=f"{AGENT_PROMPT}\n----- CURRENT_DATE_TIME: {now_time}"
    )

    response = await llm.ainvoke([system_prompt] + state["messages"][-10:])
    return {"messages": [response]}

def should_continue(state):
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tool_call"
    return "end"
    
#Graph Builder
graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)
tool_node = ToolNode(tools = tools)
graph_builder.add_node("tools", tool_node)


graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tool_call": "tools",
        "end": END
    }
)
graph_builder.add_edge("tools", "agent")

my_graph = graph_builder.compile()

