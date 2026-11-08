"""
dashboard.py

Streamlit dashboard: enter any k, press Run, see all five metrics.

    pip install streamlit
    streamlit run dashboard.py

Retrieval runs once at startup, deep (MAX_K per question), and is cached.
Every k after that is a slice of that cache, so changing k is instant.
"""

import pandas as pd
import streamlit as st

from ground_truth import GROUND_TRUTH
from metrics_utils import score_question

MAX_K = 30

st.set_page_config(page_title="RAG Retrieval Evaluation",
                   page_icon=":material/insights:", layout="wide")

# ---------------------------------------------------------------------------
# Retrieval, cached
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="loading index and retrieving…")
def load_cache():
    """Retrieve MAX_K chunks per question, once per session."""
    from langchain_ollama import OllamaEmbeddings
    from langchain_community.vectorstores import FAISS

    embeddings = OllamaEmbeddings(model="mxbai-embed-large:latest")
    store = FAISS.load_local("faiss_db", embeddings,
                             allow_dangerous_deserialization=True)

    for chunk_id, doc_id in store.index_to_docstore_id.items():
        store.docstore.search(doc_id).metadata["chunk_id"] = chunk_id

    return {item["id"]: [d.metadata["chunk_id"]
                         for d in store.similarity_search(item["question"],
                                                          k=MAX_K)]
            for item in GROUND_TRUTH}


def evaluate(cache, k):
    """Score every question at this k."""
    rows = []
    for item in GROUND_TRUTH:
        ids = cache[item["id"]][:k]
        scores = score_question(ids, item["relevant"], k)
        rows.append({
            "id": item["id"],
            "kind": item["kind"],
            "question": item["question"],
            "ground_truth": item["relevant"],
            "retrieved": ids,
            "precision": scores[f"precision@{k}"],
            "ceiling": min(len(item["relevant"]), k) / k,
            "recall": scores[f"recall@{k}"],
            "hit_rate": scores[f"hit@{k}"],
            "mrr": scores["mrr"],
            "ndcg": scores[f"ndcg@{k}"],
        })

    df = pd.DataFrame(rows)
    cols = ["precision", "ceiling", "recall", "hit_rate", "mrr", "ndcg"]
    return df, {c: round(df[c].mean(), 4) for c in cols}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("RAG Retrieval Evaluation")
st.caption(f"{len(GROUND_TRUTH)} hand-labelled questions  ·  "
           f"plain vector retrieval  ·  "
           f"chunk IDs compared against ground truth")

cache = load_cache()

if "history" not in st.session_state:
    st.session_state.history = {}

left, mid, _ = st.columns([1, 1, 4], vertical_alignment="bottom")
with left:
    k = st.number_input("chunks retrieved (k)", min_value=1,
                        max_value=MAX_K, value=3, step=1)
with mid:
    run = st.button("Run", type="primary", width="stretch",
                    icon=":material/play_arrow:")

if run or st.session_state.history:
    # Score at whatever k the input currently holds. Streamlit reruns this
    # script on every widget change, and scoring is a slice of the cached
    # retrieval plus arithmetic (~20ms), so there is nothing to gain by
    # reusing an earlier result -- and reusing one is how the cards used to
    # go stale when k was stepped back down to a value already scored.
    df, averages = evaluate(cache, k)
    st.session_state.history[k] = averages

    previous = sorted(x for x in st.session_state.history if x < k)
    prior = st.session_state.history[previous[-1]] if previous else None

    cards = [("Precision", "precision"), ("Recall", "recall"),
             ("Hit rate", "hit_rate"), ("MRR", "mrr"), ("nDCG", "ndcg")]

    for column, (label, key) in zip(st.columns(5), cards):
        delta = None
        if prior:
            change = averages[key] - prior[key]
            if abs(change) >= 0.0001:
                delta = f"{change:+.3f} vs k={previous[-1]}"
        column.metric(f"{label}@{k}", f"{averages[key]:.3f}", delta,
                      border=True)

    st.caption(f"Best precision@{k} possible on this dataset: "
               f"{averages['ceiling']:.3f}. A question with one relevant "
               f"chunk caps at {1/k:.3f}, so precision falls as k grows "
               f"even when retrieval is unchanged.")

    if len(st.session_state.history) > 1:
        st.markdown("### Metrics across every k you have run")
        curve = (pd.DataFrame(st.session_state.history).T
                   .sort_index()[["recall", "precision", "ceiling"]])
        curve.index.name = "k"
        st.line_chart(curve, height=280)

    st.markdown(f"### Every question at k = {k}")

    table = df[["id", "kind", "question", "ground_truth", "retrieved",
                "precision", "recall", "hit_rate", "mrr", "ndcg"]].copy()
    table["ground_truth"] = table["ground_truth"].apply(
        lambda v: ", ".join(map(str, v)))
    table["found"] = df.apply(
        lambda r: " ".join(f"[{c}]" if c in r["ground_truth"] else str(c)
                        for c in r["retrieved"]), axis=1)
    table = table.drop(columns=["retrieved"])

    bar = lambda label: st.column_config.ProgressColumn(
        label, min_value=0, max_value=1, format="%.2f", width="small")

    st.dataframe(
        table, width="stretch", hide_index=True, height=520,
        column_config={
            "id": st.column_config.TextColumn("id", width="small"),
            "kind": st.column_config.TextColumn("type", width="small"),
            "question": st.column_config.TextColumn("question", width="large"),
            "ground_truth": st.column_config.TextColumn("truth", width="small"),
            "found": st.column_config.TextColumn("retrieved", width="medium"),
            "precision": bar("precision"),
            "recall": bar("recall"),
            "hit_rate": bar("hit"),
            "mrr": bar("mrr"),
            "ndcg": bar("ndcg"),
        })

    st.caption("In the found column, a chunk ID with a dot in front of it "
               "was retrieved but is not in the ground truth.")
else:
    st.info("Pick a value for k and press Run. Try 1, then 3, then 10, "
            "and watch recall climb while precision drops.")