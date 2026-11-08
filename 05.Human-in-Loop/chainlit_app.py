import os
import uuid
import chainlit as cl
from typing import Dict, Optional
from langgraph_app import my_graph
from langgraph.types import Command
from hitl import RENDERERS, DEFAULT_RENDERER, UI_FORM
from chainlit.types import ThreadDict
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from langchain_core.messages import HumanMessage, AIMessage

from dotenv import load_dotenv
load_dotenv(override=True)


#Chainlit
#ChatStart
@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("state", {"messages": []})
    await cl.Message("👋 Hello! AI Assistant ready.").send()

async def stream_run(payload, config, msg_out, seen_tool_calls):
    """Stream one graph run into msg_out. Returns the assistant text produced."""
    streamed = ""

    async for chunk in my_graph.astream(
        payload,
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

        if metadata.get("langgraph_node") != "agent":
            continue

        if not message_chunk.content:
            continue

        content = message_chunk.content

        if isinstance(content, str):
            streamed += content
            await msg_out.stream_token(content)

        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    streamed += text
                    await msg_out.stream_token(text)

    return streamed


async def ask_human(payload):
    """Render an interrupt payload with the element its "ui" key names, return the answers."""
    if not isinstance(payload, dict):
        payload = {"ui": UI_FORM,
                   "questions": [{"id": "confirm", "question": str(payload),
                                  "options": [{"value": "yes", "label": "Yes"},
                                              {"value": "no", "label": "No"}]}]}

    ui = payload.get("ui", UI_FORM)
    renderer = RENDERERS.get(ui)
    if renderer is None:
        print(f"[HITL] unknown ui {ui!r}, falling back to {DEFAULT_RENDERER}")
        renderer = DEFAULT_RENDERER

    element = cl.CustomElement(name=renderer, props=payload)
    ask_msg = cl.AskElementMessage(content="", element=element, timeout=300)
    res = await ask_msg.send()

    # Drops send()'s "Thanks for submitting" stub, which lands below the answer bubble.
    await ask_msg.remove()

    # Never resume with a bare {}: LangGraph reads it as an empty interrupt-id map
    # and resumes nothing, so the interrupt re-fires forever.
    if not res or not res.get("submitted"):
        return {"cancelled": True}

    return {k: v for k, v in res.items() if k != "submitted"}


#OnMessage
@cl.on_message
async def on_message(msg: cl.Message):
    seen_tool_calls = set()
    state = cl.user_session.get("state")
    state["messages"].append(HumanMessage(content=msg.content))
    msg_out = cl.Message(content="")
    await msg_out.send()

    # Fresh thread per turn: the checkpointer only needs to survive this run,
    # conversation history is still owned by the session state above.
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    final_text = ""
    try:
        payload = {"messages": state["messages"]}

        while True:
            final_text += await stream_run(payload, config, msg_out, seen_tool_calls)

            snapshot = await my_graph.aget_state(config)
            if not snapshot.interrupts:
                break

            answers = await ask_human(snapshot.interrupts[0].value)
            payload = Command(resume=answers)

    except Exception as e:
        print("Stopped:", e)
    finally:
        if final_text: 
            msg_out.content = final_text
            await msg_out.update()

            state["messages"].append(AIMessage(content=final_text))
            cl.user_session.set("state", state)

# oAuth Authentication
@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> Optional[cl.User]:
    return default_user

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
        raise RuntimeError("DATABASE_URL not found in environment variables.")

    return SQLAlchemyDataLayer(conninfo=conninfo)
    
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