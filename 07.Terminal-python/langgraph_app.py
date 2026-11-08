# from langgraph.graph.message import add_messages
# from typing import Annotated, Sequence, TypedDict
# from langgraph.graph import StateGraph, START, END
# from langchain_core.messages import BaseMessage

# from langgraph.prebuilt import ToolNode
# from langchain_openai import ChatOpenAI
# from tools import tools

# #LLM
# llm = ChatOpenAI(
#     model="gpt-4o-mini",
#     temperature=0.2,
#     streaming = True
# ).bind_tools(tools)

# #Agent State
# class AgentState(TypedDict):
#     messages: Annotated[Sequence[BaseMessage], add_messages]

# #Node
# async def agent_node(state: AgentState):
#     response = await llm.ainvoke(state["messages"])
#     return {"messages": [response]}

# def should_continue(state):
#     last = state["messages"][-1]
#     if getattr(last, "tool_calls", None):
#         return "tool_call"
#     return "end"
    
# #Graph Builder
# graph_builder = StateGraph(AgentState)
# graph_builder.add_node("agent", agent_node)
# tool_node = ToolNode(tools = tools)
# graph_builder.add_node("tools", tool_node)


# graph_builder.add_edge(START, "agent")
# graph_builder.add_conditional_edges(
#     "agent",
#     should_continue,
#     {
#         "tool_call": "tools",
#         "end": END
#     }
# )
# graph_builder.add_edge("tools", "agent")

# my_graph = graph_builder.compile()

from tools import tools
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from dotenv import load_dotenv
load_dotenv(override=True)


my_graph = create_agent(
    model="gpt-4o-mini",
    tools=tools,
    # A checkpointer is required for interrupt() / Command(resume=...) to work
    checkpointer=MemorySaver(),
    system_prompt = """You are a helpful assistant that can run terminal commands on the user's Ubuntu machine.
    - Use the google search tool when up-to-date information is needed.
    - When a task needs a terminal command (listing files, reading files, checking versions,
      running code, etc.), call the run_terminal tool yourself. Do not tell the user to run
      normal commands. The user approves every command before it runs, so it is safe.
    - Only exception: never run commands that need admin rights (sudo, su), delete files or
      data (rm, rm -rf, rmdir, shred, dd, mkfs), or shut down the machine. For these only,
      give the user the exact command and ask them to run it in their own terminal."""
)