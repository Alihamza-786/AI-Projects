"""Human in the loop: pause the agent and ask the user before running a command."""

from langgraph.types import interrupt


def approve_command(command):
    """Ask the user about a command. Returns the command to run, or None if rejected."""

    # interrupt() pauses the graph here. The dict is sent to the UI (AskForm.jsx).
    # When the user clicks a button, the graph resumes and interrupt() returns
    # their answer, e.g. {"action": "yes"} or {"action": "edit", "command": "ls -la"}.
    answer = interrupt({"command": command})

    action = answer.get("action")

    if action == "yes":
        return command

    if action == "edit":
        return answer.get("command")

    # "no", or the user closed the form / it timed out
    return None
