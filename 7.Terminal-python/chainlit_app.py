import os
import uuid
import chainlit as cl
from langgraph_app import my_graph
from langgraph.types import Command
from chainlit.types import ThreadDict
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from langchain_core.messages import HumanMessage, AIMessage

from dotenv import load_dotenv
load_dotenv(override=True)


#ChatStart
@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("state", {"messages": []})
    await cl.Message("👋 Hello! AI Assistant ready.").send()


#Human in the loop: show AskForm.jsx and wait for the user's click
async def ask_human(interrupt_value):
    element = cl.CustomElement(name="AskForm", props=interrupt_value)
    ask_msg = cl.AskElementMessage(content="", element=element, timeout=300)
    res = await ask_msg.send()
    await ask_msg.remove()

    # Closed or timed out -> treat it as "no"
    if not res or not res.get("submitted"):
        return {"action": "no"}

    return {"action": res.get("action"), "command": res.get("command")}


#Stream one run of the graph into msg_out, return the text the model wrote
async def stream_graph(graph_input, config, msg_out, seen_tool_calls):
    text_out = ""

    async for chunk in my_graph.astream(
        graph_input,
        config=config,
        stream_mode="messages",
        version = 'v2'
    ):
        message_chunk, metadata = chunk['data']
        if hasattr(message_chunk, "tool_calls") and message_chunk.tool_calls:
            for tc in message_chunk.tool_calls:
                tool_id = tc.get("id")

                if tool_id in seen_tool_calls:
                    continue

                seen_tool_calls.add(tool_id)

                tool_name = tc.get("name")

                if not tool_name:
                    continue

                await msg_out.stream_token(
                    f"🔧 Calling tool: `{tool_name}`\n"
                )

        if metadata.get("langgraph_node") != "model":
            continue
        if not message_chunk.content:
            continue

        content = message_chunk.content

        if isinstance(content, str):
            text_out += content
            await msg_out.stream_token(content)

        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    text_out += text
                    await msg_out.stream_token(text)

    return text_out


#OnMessage
@cl.on_message
async def on_message(msg: cl.Message):
    seen_tool_calls = set()
    state = cl.user_session.get("state")
    state["messages"].append(HumanMessage(content=msg.content))
    msg_out = cl.Message(content="")
    await msg_out.send()

    # The checkpointer saves the paused graph under this thread_id so we can resume it
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    graph_input = {"messages": state["messages"]}

    final_text = ""
    try:
        # Keep running until the graph finishes without asking the user anything
        while True:
            final_text += await stream_graph(graph_input, config, msg_out, seen_tool_calls)

            # Did a tool call interrupt()? If not, the agent is done.
            snapshot = await my_graph.aget_state(config)
            if not snapshot.interrupts:
                break

            pending = snapshot.interrupts[0]
            answer = await ask_human(pending.value)

            # Resume the paused graph; interrupt() inside the tool returns `answer`
            graph_input = Command(resume={pending.id: answer})

    except Exception as e:
        print("Stopped:", e)
    finally:
        if final_text: 
            msg_out.content = final_text
            await msg_out.update()

            state["messages"].append(AIMessage(content=final_text))
            cl.user_session.set("state", state)


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
        print("\n\nMESSAGES LOADED: ", len(messages))
    except Exception as e:
    
        print(f"\nError resuming chat: {e}")
        cl.user_session.set("state", {"messages": []})