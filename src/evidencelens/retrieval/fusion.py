"""`src/evidencelens/retrieval/fusion.py`: rank fusion across retrievers.

RRF combines candidate order rather than incomparable engine-specific scores.
This keeps fusion robust when Elasticsearch and Qdrant use different score
scales; optional per-retriever weights let later evaluations tune contributions.
"""

from collections import defaultdict


def rrf(rankings: dict[str, list[str]], weights: dict[str, float] | None = None, k: int = 60) -> list[tuple[str, float]]:
    """
    Compute Reciprocal Rank Fusion (RRF) across ranked candidate lists.
    
    :dict rankings: {"es": [chunk_ids...], "qdrant": [chunk_ids...], "graph": [chunk_ids...]}
    :dict weights: Optional custom weights per retriever
    :int k: RRF smoothing constant (default = 60)
    :returns: Unique IDs sorted by descending fused score (higher ranks score more).
    """
    scores: dict[str, float] = defaultdict(float)
    weights = weights or {}
    
    for retriever_name, ids in rankings.items():
        w = weights.get(retriever_name, 1.0)
        for rank, cid in enumerate(ids, start=1):
            scores[cid] += w / (k + rank)
           
    # Sorting by the rank-only aggregate avoids comparing raw BM25 and cosine scores.
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)