# CLAUDE.md

Orientation for this directory. `README.md` explains the *retrieval metrics*
in depth and is the better read for the theory; this file is the map of what
each file is, how the pieces connect, and what breaks.

---

## What lives here

Two separate things share one FAISS index:

1. **A chat app** — Chainlit UI over a LangGraph agent that answers from the
   index (`app.py`, `chainlit_app.py`, `langgraph_app.py`).
2. **A retrieval evaluation harness** — measures how good that index's
   retrieval actually is, against hand-written labels
   (`ground_truth.py`, `metrics_utils.py`, `evaluate_baseline.py`,
   `dashboard.py`).

They do not import each other. The only shared thing is `faiss_db/`.

---

## File map

### Chat app

| File | What it is |
|---|---|
| `app.py` | FastAPI host. Mounts the Chainlit app at `/chatbot`, and a trivial `/app` endpoint. Entry point: `uvicorn app:app`. |
| `chainlit_app.py` | The Chainlit UI layer: streams graph output token by token, announces tool calls, password auth (`admin`/`admin`, hardcoded), SQLAlchemy data layer for chat history, and chat resume. |
| `langgraph_app.py` | The agent itself. One tool (`rag_retrieval`, top-3 similarity search over `faiss_db/`), `ChatOllama("qwen2.5")`, and a two-node graph: `agent` ⇄ `tools`. Exports `my_graph`. |
| `.chainlit/config.toml` | Chainlit UI config. Theme is left unset, so it follows the browser. |
| `chainlit.md` | Chainlit's welcome screen — still the stock boilerplate. |

### Evaluation harness

| File | What it is |
|---|---|
| `ground_truth.py` | The dataset: `GROUND_TRUTH`, 20 questions, each with the chunk IDs that answer it. Labels were written by reading the source document, **not** by looking at retriever output. |
| `metrics_utils.py` | Pure functions, no dependencies beyond `math`: precision@k, recall@k, hit rate@k, reciprocal rank, nDCG@k, plus `score_question()` which returns all five. |
| `evaluate_baseline.py` | Script-style run: scores every question at one k, sweeps recall across k, prints tables, writes `results.json`. Call `main(vectorstore)` with a loaded FAISS store. |
| `dashboard.py` | The Streamlit dashboard. Pick a k, press Run, see all five metrics, a curve across every k you have tried, and a per-question table. |
| `.streamlit/config.toml` | The dashboard's theme. See **Theming** below. |
| `results.json` | Last saved output of `evaluate_baseline.py`. Has `baseline` / `rerank` sections plus per-question rows and the recall curve. |

### Data and index

| Path | What it is |
|---|---|
| `faiss_db/` | The FAISS vector store. **Not rebuilt by anything here** — build it from the ingestion notebook. |
| `space_data/` | Source documents the index was built from: the space-exploration doc (chunks 0–58) and the NovaTech handbook (chunks 59–67). |
| `nova_data/` | A second document set (company txt, FAQ json, employees csv, handbook docx, architecture pdf) used by the ingestion notebook. |
| `.files/` | Chainlit's upload directory. Empty. |

### Notebooks

| Notebook | What it is |
|---|---|
| `1.Injestion_pipeline.ipynb` | Builds the index: loaders → `RecursiveCharacterTextSplitter` → `OllamaEmbeddings` → FAISS. This is what produces `faiss_db/`. |
| `2.helpfull_material.ipynb` | Long-form teaching version of the same ingestion material, with explanation cells. |
| `Advance-RAG.ipynb` | Reranking experiments with `CohereRerank` (`rerank-v3.5`). Needs `CO_API_KEY`. |

---

## The chunk_id convention

This is the thing most likely to trip you up.

FAISS documents do not carry an ID by default. Both `evaluate_baseline.py`
(`add_chunk_ids`) and `dashboard.py` (`load_cache`) walk
`store.index_to_docstore_id` and write the FAISS row number into each
document's `metadata["chunk_id"]` before retrieving. Every metric then
compares plain integers.

**Those integers are positional.** If the index is rebuilt with different
chunking, every label in `ground_truth.py` silently becomes wrong — the
numbers still line up, they just point at different text. Re-chunking means
re-labelling by hand. There is no check that catches this.

---

## Running things

```bash
# Chat app (Chainlit UI at http://localhost:8000/chatbot)
uvicorn app:app --reload

# Dashboard
streamlit run dashboard.py

# Baseline numbers -> results.json
python -c "
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
import evaluate_baseline as e
s = FAISS.load_local('faiss_db', OllamaEmbeddings(model='mxbai-embed-large:latest'),
                     allow_dangerous_deserialization=True)
e.main(s)"
```

Dependencies live in the shared venv one level up (`../venv`), which is why
`streamlit`/`langchain` are not importable from the system Python.

### Requires a running Ollama

Both halves need `ollama serve` with two models pulled:

- `mxbai-embed-large:latest` — embeddings. Must be the **same** model the
  index was built with, or every search result is noise.
- `qwen2.5` — the chat model, agent side only.

### Secrets

`.env` (gitignored) holds `DATABASE_URL` and `CHAINLIT_AUTH_SECRET` for chat
history, `CO_API_KEY` for the reranking notebook, and OAuth/API keys carried
over from sibling projects in this repo. `chainlit_app.py` degrades to no
history if `DATABASE_URL` is missing; it does not crash.

---

## Dashboard behaviour worth knowing

- `load_cache()` is `@st.cache_resource` and retrieves `MAX_K` (30) chunks per
  question **once at startup**. Every k after that is a slice of that cache,
  so changing k is instant and costs no Ollama calls. Startup is the slow part.
- Every rerun scores at whatever `k` the input currently holds, so the cards,
  the caption and the table always agree with the input. `st.session_state.
  history` accumulates `{k: averages}` purely to feed the delta and the chart:
  the delta compares against the nearest smaller k you have already run, and
  the line chart appears once two or more k values are in history.
- The Run button is not the only trigger. Any widget change reruns the script,
  so stepping `k` with the +/- buttons updates everything on its own; Run just
  forces the first evaluation when nothing has been scored yet.
- `ceiling` is `min(len(relevant), k) / k` — the best precision@k this dataset
  allows. Precision must fall as k rises; that is arithmetic, not a regression.

---

## Theming

The dashboard's look is **entirely** in `.streamlit/config.toml` — colours,
fonts, radii, chart palette. Do not add CSS via
`st.markdown(..., unsafe_allow_html=True)` or `st.html()` to restyle it.
Native theme tokens apply to every widget consistently and survive Streamlit
upgrades; CSS targets internal class names that do not.

Only `[theme]` is defined and no `[theme.dark]`, which deliberately locks the
app to light mode regardless of the viewer's OS setting.

`chartCategoricalColors` is a validated palette: adjacent pairs clear the
colour-vision-deficiency separation floor against a white surface. Altair
assigns those colours to series **alphabetically**, so on the metrics chart
`ceiling` is blue, `precision` orange, `recall` aqua. Reordering the DataFrame
columns will not change that; only renaming the series would.

---

## Known rough edges

- `dashboard.py`'s closing caption says a non-ground-truth chunk ID has "a dot
  in front of it", but the code brackets the ground-truth ones instead
  (`f"[{c}]"`). The caption describes the opposite of what renders.
- Streamlit reruns the whole script on every widget change, so `k` changing is
  a rerun, not an event. `dashboard.py` therefore re-scores on each rerun
  rather than reusing a stored result. It used to skip scoring when `k` was
  already in `history` and render a stashed `session_state.last` instead,
  which made the cards show a stale `k` whenever you stepped `k` back down.
  Scoring is ~20ms, so caching it buys nothing — do not reintroduce that.
- Colouring individual chunk IDs inside the retrieved cell is **not possible**
  in `st.dataframe`: the grid draws every cell as plain text, and
  `MarkdownColumn` renders markdown only in a click-through overlay, not in
  the cell. `:green[...]`, inline HTML and `**bold**` all come out literal.
  Getting inline colour means hand-building the table in `st.html()`, which
  costs sorting, resizing and CSV download — tried, then reverted.
- `chainlit_app.py` auth is `admin`/`admin` in source. Fine locally, not
  elsewhere.
- `results.json` has a `rerank` section that nothing in the `.py` files writes
  — it came from notebook work.
