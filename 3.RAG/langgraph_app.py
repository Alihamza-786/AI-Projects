from langchain_ollama import ChatOllama
from langgraph.graph.message import add_messages
from typing import Annotated, Sequence, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS


embeddings = OllamaEmbeddings(
    model="mxbai-embed-large:latest"   
)

vectorstore = FAISS.load_local(
    "faiss_db",
    embeddings,
    allow_dangerous_deserialization=True
)


#rag
@tool
def rag_retrieval(query: str):
    """Search the company knowledge base and return relevant information."""
    print("\n*************RAG*************")

    results = vectorstore.similarity_search_with_score(query, k=3)

    filtered = [
        doc.page_content
        for doc, score in results
    ]
    return "\n\n---\n\n".join(filtered) if filtered else "No relevant context found."

tools = [rag_retrieval]


#LLM
llm = ChatOllama(
    model="qwen2.5",
    temperature=0.5,
).bind_tools(tools)

#Agent State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

#Node
async def agent_node(state: AgentState):
    response = await llm.ainvoke(state["messages"])
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

