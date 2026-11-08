"""
Retrieval metrics.

    retrieved  chunk IDs returned by the retriever, in rank order
    relevant   chunk IDs that are actually relevant (ground truth)
    k          how many of the retrieved results to score
"""

import math


def precision_at_k(retrieved, relevant, k):
    """Of the k chunks retrieved, what fraction is relevant?

    How much of what we sent the LLM was useful.
    Ceiling is min(len(relevant), k) / k, so a single-answer
    question caps at 1/k.
    """
    top_k = retrieved[:k]

    found = 0
    for chunk in top_k:
        if chunk in relevant:
            found += 1

    return found / k


def recall_at_k(retrieved, relevant, k):
    """Of all relevant chunks, what fraction is in the top k?

    Whether we missed anything the LLM needed.
    """
    top_k = retrieved[:k]

    found = 0
    for chunk in relevant:
        if chunk in top_k:
            found += 1

    return found / len(relevant)


def hit_rate_at_k(retrieved, relevant, k):
    """1 if any relevant chunk is in the top k, else 0.

    Whether retrieval failed outright. Saturates easily.
    """
    top_k = retrieved[:k]

    for chunk in top_k:
        if chunk in relevant:
            return 1

    return 0


def reciprocal_rank(retrieved, relevant):
    """1 / position of the first relevant chunk, 0 if none.

    How soon we hit something useful. Averaged over all
    questions this is MRR. Scans the whole list passed in,
    so pass the same list you score everything else on.
    """
    for position, chunk in enumerate(retrieved, start=1):
        if chunk in relevant:
            return 1 / position

    return 0


def ndcg_at_k(retrieved, relevant, k):
    """Position-weighted precision, normalised to a perfect ranking.

    Each hit is worth 1 / log2(position + 1), so rank 1 beats
    rank 3. DCG is what we got, IDCG is the best possible,
    nDCG is the ratio. 1.0 means optimally ordered.
    """
    top_k = retrieved[:k]

    dcg = 0
    for position, chunk in enumerate(top_k, start=1):
        if chunk in relevant:
            dcg += 1 / math.log2(position + 1)

    idcg = 0
    for position in range(1, min(len(relevant), k) + 1):
        idcg += 1 / math.log2(position + 1)

    if idcg == 0:
        return 0

    return dcg / idcg


def score_question(retrieved, relevant, k):
    """All five metrics for one question."""
    return {
        f"precision@{k}": precision_at_k(retrieved, relevant, k),
        f"recall@{k}": recall_at_k(retrieved, relevant, k),
        f"hit@{k}": hit_rate_at_k(retrieved, relevant, k),
        "mrr": reciprocal_rank(retrieved, relevant),
        f"ndcg@{k}": ndcg_at_k(retrieved, relevant, k),
    }