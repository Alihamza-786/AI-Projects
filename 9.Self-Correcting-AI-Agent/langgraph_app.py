"""Multi-agent coding team: a main agent delegates work to a coder agent and a tester agent."""

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.tools import tool

from prompts import CODER_PROMPT, MAIN_PROMPT, TESTER_PROMPT
from tools import coder_tools, read_code, run_all_tests, tester_tools
from utils import pytest_summary

load_dotenv(override=True)

MODEL = "gpt-4.1-mini"
MAX_FIX_ROUNDS = 3  # coder: 1 first version + 3 fixes


# ---------------- Sub-agents ----------------
# No checkpointer: each call starts fresh. The files in sandbox/ are their shared memory.

coder_agent = create_agent(
    model=MODEL,
    tools=coder_tools,
    system_prompt=CODER_PROMPT,
    name="coder",
)

tester_agent = create_agent(
    model=MODEL,
    tools=tester_tools,
    system_prompt=TESTER_PROMPT,
    name="tester",
)


# ---------------- Sub-agents wrapped as tools ----------------

@tool
async def ask_coder(instruction: str) -> str:
    """Ask the coder agent to write solution.py or fix it.
    For fixes, include the task and the failed tests exactly as given."""
    result = await coder_agent.ainvoke({"messages": [{"role": "user", "content": instruction}]})
    return result["messages"][-1].content


@tool
async def ask_tester(instruction: str) -> str:
    """Ask the tester agent to write tests (first time) or rerun them.
    Include the full task. Returns a VERIFIED RESULT plus the tester's summary."""
    result = await tester_agent.ainvoke({"messages": [{"role": "user", "content": instruction}]})
    tester_summary = result["messages"][-1].content

    # Never trust an LLM's claim about test results: run pytest ourselves and report the truth.
    passed, report = run_all_tests()
    if report.startswith("SETUP ERROR"):
        return report

    counts, failed = pytest_summary(report)
    status = "ALL TESTS PASSED" if passed else "TESTS FAILED"
    verified = f"VERIFIED RESULT: {status} ({counts})"
    if failed:
        verified += "\n" + "\n".join(failed)

    return f"{verified}\n\nTester's summary:\n{tester_summary}"

# ---------------- Main agent ----------------

my_graph = create_agent(
    model=MODEL,
    tools=[ask_coder, ask_tester, read_code],
    system_prompt=MAIN_PROMPT,
    middleware=[
        # The LLM decides when to retry, so the code sets a hard limit.
        ToolCallLimitMiddleware(tool_name="ask_coder", run_limit=1 + MAX_FIX_ROUNDS),
        ToolCallLimitMiddleware(tool_name="ask_tester", run_limit=2 + MAX_FIX_ROUNDS),  # +1 for a disputed test
    ],
    name="main",
)
