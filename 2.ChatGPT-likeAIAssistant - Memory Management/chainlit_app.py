import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage
import os
from chainlit.types import ThreadDict
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

from langgraph_app import graph

from dotenv import load_dotenv
load_dotenv(override=True)


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
    state["messages"] = state["messages"][-10:]
    print("\n\nSTATE: ", state)
    print("\nLENGTH:", len(state['messages']))
    msg_out = cl.Message(content="")
    await msg_out.send()

    final_text = ""
    try: 
        async for chunk in graph.astream(
            {"messages": state["messages"]},
            stream_mode="messages",
            version = 'v2'
        ):
            message_chunk, metadata = chunk['data']

            if message_chunk.content:
                final_text += message_chunk.content
                await msg_out.stream_token(message_chunk.content)

    except Exception as e:
        print("Stopped:", e)
    finally:
        if final_text: 
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
        print("\n\nMESSAGES LOADED: ", len(messages))
    except Exception as e:
    
        print(f"\nError resuming chat: {e}")
        cl.user_session.set("state", {"messages": []})