"""Deep research team: a lead agent plans the work, a researcher agent searches the web,
and a verifier agent checks every finding on official sources."""

from datetime import date

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, TodoListMiddleware
from langchain_core.tools import tool

from prompts import MAIN_PROMPT, RESEARCHER_PROMPT, VERIFIER_PROMPT
from tools import researcher_tools, verifier_tools
from utils import FINDINGS, check_citations, check_verdicts

load_dotenv(override=True)

MODEL = "gpt-4o-mini"
TODAY = date.today().isoformat()   # the LLM does not know today's date, so we tell it


# ---------------- Sub-agents ----------------
# No checkpointer: each call starts fresh. The lead must send the full context every time.

researcher_agent = create_agent(
    model=MODEL,
    tools=researcher_tools,
    system_prompt=RESEARCHER_PROMPT.format(today=TODAY),
    middleware=[
        # Every search/extract costs Tavily credits, so the code sets a hard limit.
        ToolCallLimitMiddleware(tool_name="web_search", run_limit=3),
        ToolCallLimitMiddleware(tool_name="extract_page", run_limit=4),
    ],
    name="researcher",
)

verifier_agent = create_agent(
    model=MODEL,
    tools=verifier_tools,
    system_prompt=VERIFIER_PROMPT.format(today=TODAY),
    middleware=[
        ToolCallLimitMiddleware(tool_name="official_search", run_limit=8),
        ToolCallLimitMiddleware(tool_name="extract_page", run_limit=8),
    ],
    name="verifier",
)


# ---------------- Sub-agents wrapped as tools ----------------

@tool
async def ask_researcher(sub_question: str) -> str:
    """Ask the researcher agent to research ONE sub-question on the web.
    Include the user's full goal. Returns findings with sources, plus a CITATION CHECK."""
    result = await researcher_agent.ainvoke({"messages": [{"role": "user", "content": sub_question}]})
    reply = result["messages"][-1].content
    FINDINGS.append(reply)   # our code keeps the findings exactly as written, for the verifier

    # Never trust an LLM's citations: our code checks which pages were really read.
    return f"{reply}\n\n{check_citations(reply)}"


@tool
async def ask_verifier() -> str:
    """Ask the verifier agent to check ALL findings of the researchers on official sources.
    No input needed: our code sends the findings. Returns VERIFIED / NOT VERIFIED / NOT CHECKED per finding."""
    if not FINDINGS:
        return "There are no findings yet. Call ask_researcher first."

    # Our code passes the findings, so the lead cannot change or invent anything on the way.
    findings = "\n\n".join(FINDINGS)
    result = await verifier_agent.ainvoke({"messages": [{"role": "user", "content": findings}]})
    reply = result["messages"][-1].content

    # Never trust an LLM's verdict: our code re-checks every VERIFIED line and corrects it if needed.
    reply, verdict_report = check_verdicts(reply)
    return f"{reply}\n\n{verdict_report}\n\n{check_citations(reply)}"


# ---------------- Main agent ----------------

my_graph = create_agent(
    model=MODEL,
    tools=[ask_researcher, ask_verifier],
    system_prompt=MAIN_PROMPT.format(today=TODAY),
    middleware=[
        TodoListMiddleware(),   # gives the lead a write_todos tool (like a checklist) to plan its work
        ToolCallLimitMiddleware(tool_name="ask_researcher", run_limit=4),
        ToolCallLimitMiddleware(tool_name="ask_verifier", run_limit=2),
    ],
    name="main",
)
