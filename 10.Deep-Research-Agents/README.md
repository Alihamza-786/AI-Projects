# Deep Research Agent

A multi-agent research assistant. You ask a research question, and a team of 3 AI agents searches the web, reads the pages, checks the facts on official websites, and writes a report with sources.

Example questions:
- *Identify the major US companies developing AI agents in 2027. Categorize them by industry, with evidence from official sources.*
- *What is Model Context Protocol (MCP), why was it introduced, and how is it different from traditional APIs?*
- *Compare LangGraph, CrewAI and AutoGen: architecture, strengths, weaknesses, ideal use cases.*

---

## How it works

```
User
 └─► Lead agent          plans, delegates, writes the report
       ├─► Researcher agent   searches the web and reads pages
       └─► Verifier agent     checks each finding on the official website
```

| Agent | Job | Tools |
|---|---|---|
| **Lead** | Splits the question into 2-4 sub-questions (a todo list), sends them to researchers, sends the findings to the verifier, writes the report | `write_todos`, `ask_researcher`, `ask_verifier` |
| **Researcher** | **Search → Extract → Analyze**: finds pages, reads the best ones, writes findings (fact, who it is about, evidence quote, source) | `web_search`, `extract_page` |
| **Verifier** | Checks every finding on the official website of whoever it is about (e.g. `anthropic.com`). Marks it VERIFIED, NOT VERIFIED or NOT CHECKED | `official_search`, `extract_page` |

**Search vs Extract** (both use the [Tavily](https://tavily.com) API):
- `web_search`: "which pages talk about this?" Returns titles, URLs and short snippets.
- `extract_page`: "what does this page say?" Returns the full text of one page.
- `official_search`: a search limited to one official website.

### The LLM does the work, our code checks it
LLMs can invent URLs or say "verified" when they are not sure. So our Python code checks them (`utils.py`):
- **Citation check**: every URL an agent cites must be a page that `extract_page` really read. If not, it is flagged as `⚠ NOT READ`.
- **Verdict check**: every ✅ must come from a page that was really read **and** is on the official domain. If not, the code changes it to NOT VERIFIED.
- **Findings hand-off**: our code (not the lead) passes the researchers' findings to the verifier, so nothing is changed on the way.
- **Limits**: `ToolCallLimitMiddleware` caps how many times each tool can be called. This stops loops and saves API credits.

Open **`workflow.html`** in a browser for a step-by-step animated diagram.

---

## Files

| File | What it contains |
|---|---|
| `app.py` | FastAPI app that mounts the Chainlit chat at `/chatbot` |
| `chainlit_app.py` | Chat UI: live status line, todo checklist, research log, login, chat history |
| `langgraph_app.py` | The 3 agents, and the `ask_researcher` / `ask_verifier` tools that connect them |
| `tools.py` | The Tavily tools: `web_search`, `extract_page`, `official_search` |
| `prompts.py` | The system prompts of the 3 agents |
| `utils.py` | Memory of pages read and findings, plus the citation and verdict checks |
| `workflow.html` | Animated diagram of the workflow |
| `.chainlit/`, `public/` | Chainlit config, theme and logo |

---

## Mandatory setup

### 1. Python packages
Python 3.10+ is needed. From the project folder:
```bash
pip install chainlit fastapi uvicorn python-dotenv \
            langchain langgraph langchain-openai langchain-tavily \
            sqlalchemy asyncpg
```

### 2. API keys
Copy `.env.example` to `.env` and fill in:

| Variable | Mandatory | Where to get it |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Yes | https://platform.openai.com/api-keys |
| `TAVILY_API_KEY` | ✅ Yes | https://app.tavily.com (free tier available) |
| `CHAINLIT_AUTH_SECRET` | ✅ Yes (login is on) | Run `chainlit create-secret` in the terminal |
| `DATABASE_URL` | Optional | A PostgreSQL URL, to save chat history. Without it the chat still works, but history is not saved. |

`.env` contains secrets: never commit it to Git.

### 3. Run
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```
Open **http://localhost:8000/chatbot** and log in with **admin / admin**.

Or run only the chat, without FastAPI:
```bash
chainlit run chainlit_app.py -w
```

If port 8000 is busy (for example an older project is still running), stop it with `Ctrl+C` or use another port.

---

## Settings you can change

| What | Where |
|---|---|
| The LLM model | `MODEL` in `langgraph_app.py` (default `gpt-4o-mini`) |
| How many calls each tool may make | `run_limit=` in `langgraph_app.py` |
| How much page text the LLM gets | `MAX_PAGE_CHARS` in `utils.py` |
| Sites that are never used as evidence | `EXCLUDED_DOMAINS` in `utils.py` |
| How the agents behave | `prompts.py` |

## Good to know
- One research question takes about **1 minute** and uses about **15-30 Tavily credits**.
- Many findings may come back ❌ **not verified**. This is the checks working: the claim came from a blog, not from an official page.
- The terminal message `SQLAlchemy: create_element error. No blob_storage_client` is harmless. It only means the todo checklist is not saved in the chat history.
