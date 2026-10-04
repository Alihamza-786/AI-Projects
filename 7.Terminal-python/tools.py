
import subprocess
from hitl import approve_command
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from utils import BLOCKED_MESSAGE, is_blocked

tavily = TavilySearch(max_results = 2)

#google search
@tool
def google_search(query: str):
    """This tool is used to do the google search"""
    print("\n*************Google Search*************")

    result = tavily.invoke(query)
    return result

#run_terminal
@tool
def run_terminal(command: str) -> str:
    """Execute a shell command on Ubuntu and return its output."""
    # Safety check 1: never even ask the user about a blocked command.
    if is_blocked(command):
        return BLOCKED_MESSAGE.format(command=command)


    approved_command = approve_command(command)

    if not approved_command:
        return "The user rejected this command, so it was not run."

    # Safety check 2: the user may have edited it into a blocked command.
    # Say the user made the edit, otherwise the LLM gets confused and answers from old messages.
    if is_blocked(approved_command):
        return (
            f"Your command `{command}` was NOT run, because the user edited it into `{approved_command}`. "
            + BLOCKED_MESSAGE.format(command=approved_command)
        )

    # If the user edited the command, tell the LLM clearly
    note = ""
    if approved_command != command:
        note = (
            f"NOTE: The user edited your command from `{command}` to `{approved_command}`. "
            f"The output below is from `{approved_command}`. Do not run `{command}` again.\n\n"
        )
    command = approved_command

    print(f"\n*************Terminal: {command}*************")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        return (
            note +
            f"COMMAND RUN: {command}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}\n"
            f"EXIT CODE: {result.returncode}"
        )

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."


#tools list
tools = [google_search, run_terminal]