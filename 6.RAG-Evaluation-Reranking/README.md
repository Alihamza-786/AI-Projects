# RAG Retrieval Evaluation

Measure how well the retrieval half of a RAG pipeline actually works, and
watch precision and recall pull against each other as you change how many
chunks you fetch.

Most RAG tutorials stop at "it returned something relevant." This measures
it: 20 hand-labelled questions, five standard information-retrieval
metrics, and a dashboard where you set `k` and see what changes.

---

## The idea

For every question we know, in advance, which chunks in the vector store
contain the answer. That list is the ground truth. Retrieval then runs and
we compare what came back against what should have come back.

Labels were written by reading the source document, **not** by looking at
what the retriever returned. That order matters. If you mark a chunk
relevant because retrieval ranked it first, your metrics can only ever
confirm what the retriever already does.

---

## Files

| File | What it holds |
|---|---|
| `ground_truth.py` | 20 questions, each with the chunk IDs that answer it |
| `metrics_utils.py` | precision, recall, hit rate, MRR, nDCG |
| `dashboard.py` | Streamlit app: pick a `k`, see every metric |
| `faiss_db/` | the vector store (not in this repo, build it yourself) |

---

## Running it

```bash
pip install streamlit langchain-community langchain-ollama faiss-cpu pandas
streamlit run dashboard.py
```

The index is loaded and searched once at startup, 30 chunks per question,
and cached. Changing `k` after that is a slice of that cache, so it
responds instantly. `MAX_K` at the top of `dashboard.py` sets the limit.

`dashboard.py` expects a FAISS store in `faiss_db/` built with the
`mxbai-embed-large` Ollama embedding model. Change the two lines in
`load_cache()` if you use something else. Chunk IDs must match the ones in
`ground_truth.py`, so if you re-chunk the document every label becomes
invalid and has to be redone.

---

## The metrics

All five take the chunk IDs the retriever returned, the chunk IDs that are
actually relevant, and `k`.

**Precision@k** — of the k chunks we sent the LLM, what fraction was
relevant? Measures how much noise we are passing along.

**Recall@k** — of all the relevant chunks that exist, what fraction did we
find? Measures whether the LLM had enough to answer.

**Hit rate@k** — did we find at least one relevant chunk? 1 or 0. The
easiest metric to pass, so it saturates quickly and stops being useful.

**MRR** — 1 divided by the rank of the first relevant chunk. Rank 1 scores
1.0, rank 2 scores 0.5. Measures how soon something useful appears.

**nDCG@k** — like precision but position-aware: a hit at rank 1 counts for
more than the same hit at rank 3. Normalised against a perfect ranking, so
1.0 means optimally ordered.

---

## Reading the numbers

**Precision has a ceiling below 1.0.** A question with one relevant chunk
can score at most `1/k`. At k=10 that is 0.10. So precision *always* falls
as k rises, even when retrieval is unchanged, and comparing it against 1.0
is meaningless. The dashboard shows the ceiling next to the measured value
for exactly this reason.

**Recall rises with k and precision falls.** That trade-off is the central
fact of retrieval. Fetch more and you find more of the answer, but a
smaller share of what you send is useful. Try k=1, then k=3, then k=10 and
watch both move.

**Hit rate and MRR saturate.** Once they read 1.0 across the dataset there
is no information left in them, and no amount of reranking or query
rewriting will move them. Worth knowing before you spend a week on a
technique that cannot help.

**A metric that does not move is still a result.** If recall@10 is already
0.96, the most any reranker can do is reorder within that ceiling. Measure
the ceiling first and you will know what is worth trying.

---

## Question types

Each question is tagged so failures can be traced to a cause rather than
averaged away.

- `single` — the answer sits in one chunk
- `multi_chunk` — the answer is spread across several
- `paraphrase` — the question wording differs from the document
- `multi_hop` — facts must be combined from separate places
- `other_document` — the answer is in a different source document

Questions with one relevant chunk score near-perfectly on almost any
retriever, so they drag averages up and hide real problems. The multi-chunk
and paraphrase questions are where the interesting failures live.

---

## Adding your own questions

```python
{
    "id": "q21",
    "kind": "single",
    "question": "Your question here?",
    "relevant": [12, 34],
    "reference_answer": "What a correct answer looks like.",
}
```

Read the document, find the chunks that answer it, list their IDs. Do not
run retrieval first.
