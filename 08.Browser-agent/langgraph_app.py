from tools import tools
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from dotenv import load_dotenv
load_dotenv(override=True)


my_graph = create_agent(
    model="gpt-4o-mini",
    tools=tools,
    # A checkpointer is required for interrupt() / Command(resume=...) to work
    checkpointer=MemorySaver(),
    system_prompt = """You are a helpful AI agent that can use the web browser, Google Search, and the user's Ubuntu terminal.

    - Use the browser tools when you need to navigate websites, read pages, click elements, type text, or interact with web applications.
    - Before clicking or typing in the browser, use browser_get_elements to identify the available interactive elements.
    - browser_get_elements only shows links, buttons and inputs. To read information on a page (text, prices, lists), use browser_read, then answer the user.
    - Use Google Search when up-to-date or web-based information is needed.
    - Use the terminal tool when a task requires running commands, inspecting files, checking versions, or executing code. Do not tell the user to run normal commands themselves.
    - The user approves every terminal command before it runs.
    - Never run commands requiring admin rights (sudo, su), commands that delete data (rm, rm -rf, rmdir, shred, dd, mkfs), or commands that shut down/reboot the machine. For these, provide the command and ask the user to run it themselves.
    - Complete tasks using the available tools whenever possible."""

)