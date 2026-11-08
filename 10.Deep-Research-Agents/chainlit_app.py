import os
import random
import time
import chainlit as cl
from langgraph_app import my_graph
from utils import get_domain, reset_sources
from chainlit.types import ThreadDict
from chainlit.utils import utc_now
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from langchain_core.messages import HumanMessage, AIMessage

from dotenv import load_dotenv
load_dotenv(override=True)


# Todo status from LangChain -> Chainlit task status
TODO_STATUS = {
    "pending": cl.TaskStatus.READY,
    "in_progress": cl.TaskStatus.RUNNING,
    "completed": cl.TaskStatus.DONE,
}

# One icon per tool for the research log
ICONS = {
    "ask_researcher": "🧑‍💼",
    "ask_verifier": "🧑‍💼",
    "web_search": "🔍",
    "extract_page": "📄",
    "official_search": "🏛️",
}

# Shown while the lead's LLM is thinking (like Claude's "Thinking… / Harnessing…")
THINKING_WORDS = ["Thinking", "Pondering", "Harnessing", "Brewing", "Connecting the dots"]


#ChatStart
@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("state", {"messages": []})
    await cl.Message(
        "👋 Hello! Ask me a research question. A researcher agent searches the web, "
        "a verifier agent checks the facts on official websites, and I write the report."
    ).send()


#Show the lead agent's todo list (from write_todos) as a live checklist
async def show_todos(todos, all_todos, task_list):
    new = {todo["content"]: todo["status"] for todo in todos}

    # Safety net: if the LLM dropped a todo from the list, keep it and show it as done
    for title in all_todos:
        if title not in new:
            all_todos[title] = "completed"
    all_todos.update(new)

    task_list.tasks = []
    for title, status in all_todos.items():
        await task_list.add_task(cl.Task(title=title, status=TODO_STATUS[status]))

    done = sum(status == "completed" for status in all_todos.values())
    task_list.status = f"Research plan: {done}/{len(all_todos)} done"
    await task_list.send()


#One readable line per tool call: which agent, which tool, and what it searched or read
def describe_tool_call(agent_name, tool_call):
    tool_name, args = tool_call["name"], tool_call["args"]
    if tool_name == "write_todos":
        return None   # shown as the checklist instead

    agent = "lead" if agent_name in (None, "main") else agent_name
    detail = args.get("query") or args.get("url") or args.get("sub_question") or ("all findings" if tool_name == "ask_verifier" else "")
    detail = detail.replace("\n", " ")
    if len(detail) > 100:
        detail = detail[:100] + "…"
    if tool_name == "official_search":
        detail = f"[{args.get('domain')}] {detail}"

    return f"{ICONS.get(tool_name, '🔧')} **{agent}** → `{tool_name}`: {detail}"


#One short status line per tool call, for the live status
def status_for(tool_call):
    tool_name, args = tool_call["name"], tool_call["args"]

    if tool_name == "write_todos":
        return "📝 Planning the research…"
    if tool_name == "ask_researcher":
        return "🧑‍💼 Researchers at work…"
    if tool_name == "web_search":
        return f"🔍 Searching: \"{args.get('query', '')}\"…"
    if tool_name == "extract_page":
        return f"📄 Reading {get_domain(args.get('url', ''))}…"
    if tool_name == "ask_verifier":
        return "🏛️ Verifying findings on official websites…"
    if tool_name == "official_search":
        return f"🏛️ Checking {args.get('domain', '')}…"
    return f"🔧 {tool_name}…"


#Live status: replace the text of msg_out (the old status disappears, the new one appears)
async def set_status(msg_out, text, started):
    seconds = int(time.time() - started)
    msg_out.content = f"*{text}* ({seconds}s)"
    await msg_out.update()


#Stream the graph: tool calls go into the research log and the live status, the lead's report goes into msg_out
async def stream_graph(graph_input, msg_out, log, all_todos, task_list):
    text_out = ""
    writing = False          # becomes True when the lead starts writing the report
    started = time.time()
    await set_status(msg_out, "🤔 Thinking…", started)

    async for chunk in my_graph.astream(
        graph_input,
        stream_mode=["messages", "updates"],   # messages = tokens, updates = finished steps
        subgraphs=True,   # also see the researcher and verifier agents
        version='v2'
    ):
        from_main = len(chunk['ns']) == 0   # empty namespace = main agent, else a sub-agent

        # "updates" = a step has finished. Its messages are complete, with all tool-call arguments.
        if chunk['type'] == "updates":
            for node, update in chunk['data'].items():
                if not isinstance(update, dict):
                    continue

                # The todo list is saved in the state after write_todos runs
                if from_main and "todos" in update:
                    await show_todos(update["todos"], all_todos, task_list)

                for message in update.get("messages", []):
                    for tool_call in getattr(message, "tool_calls", None) or []:
                        line = describe_tool_call(message.name, tool_call)   # message.name = agent name
                        if line:
                            await log.stream_token(line + "\n\n")
                        if not writing:
                            await set_status(msg_out, status_for(tool_call), started)

                # The lead's tools are done, so the lead's LLM is thinking about the next step
                if from_main and node == "tools" and not writing:
                    await set_status(msg_out, f"🤔 {random.choice(THINKING_WORDS)}…", started)
            continue

        # "messages" = tokens. Only the main agent's own words go into the answer.
        message_chunk, metadata = chunk['data']
        if not from_main:
            continue
        if metadata.get("langgraph_node") != "model":
            continue
        if not message_chunk.content:
            continue

        # First word of the report: remove the status line, the report takes its place
        if not writing:
            writing = True
            msg_out.content = ""

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
    reset_sources()   # every message is a new question with an empty page memory

    state = cl.user_session.get("state")
    state["messages"].append(HumanMessage(content=msg.content))

    task_list = cl.TaskList()
    all_todos = {}   # every todo seen during this question: title -> status

    # Collapsible "Research log" step above the answer: every search and page read goes here
    log = cl.Step(name="Research log", type="tool")
    log.start = utc_now()
    await log.send()

    msg_out = cl.Message(content="")
    await msg_out.send()

    graph_input = {"messages": state["messages"]}

    final_text = ""
    try:
        final_text = await stream_graph(graph_input, msg_out, log, all_todos, task_list)

    except Exception as e:
        print("Stopped:", e)
        msg_out.content = f"⚠️ Stopped: {e}"   # do not leave an old status line on the screen
        await msg_out.update()
    finally:
        log.end = utc_now()
        if log.output:
            await log.update()
        else:
            await log.remove()   # no tools were used (for example "hi"), so hide the empty log

        if final_text:
            msg_out.content = final_text
            await msg_out.update()

            # The report is written, so the whole plan is done (the LLM does not always tick every todo)
            if task_list.tasks:
                for task in task_list.tasks:
                    task.status = cl.TaskStatus.DONE
                task_list.status = "Research done ✅"
                await task_list.send()

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
