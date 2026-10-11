# src/evidencelens/retrieval/fusion.py
from collections import defaultdict


def rrf(rankings: dict[str, list[str]], weights: dict[str, float] | None = None, k: int = 60) -> list[tuple[str, float]]:
    """
    Computes Reciprocal Rank Fusion (RRF) across multiple retriever result lists.
    
    :dict rankings: {"es": [chunk_ids...], "qdrant": [chunk_ids...], "graph": [chunk_ids...]}
    :dict weights: Optional custom weights per retriever
    :int k: RRF smoothing constant (default = 60)
    :returns: Sorted list of tuples (chunk_id, fused_score)
    """
    scores: dict[str, float] = defaultdict(float)
    weights = weights or {}
    
    for retriever_name, ids in rankings.items():
        w = weights.get(retriever_name, 1.0)
        for rank, cid in enumerate(ids, start=1):
            scores[cid] += w / (k + rank)
           
    # Sort by fused score descending
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)