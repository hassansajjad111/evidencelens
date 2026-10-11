"""`tests/test_fusion.py`: rank-fusion behavior tests without live services."""

from evidencelens.retrieval.fusion import rrf


def test_rrf_basic():
    """Verify fusion combines multiple rankings and returns deterministic ordering."""
    # Mock rankings from two retrievers
    rankings = {
        "es": ["doc_A", "doc_B", "doc_C"],
        "qdrant": ["doc_B", "doc_D", "doc_A"]
    }
    
    # Run fusion with default k=60
    fused = rrf(rankings, k=60)
    
    # doc_B is rank 1 in qdrant and rank 2 in es -> should float to the very top
    # doc_A is rank 1 in es and rank 3 in qdrant -> should also be very high
    top_doc, _ = fused[0]
    
    assert top_doc in ["doc_B", "doc_A"], "Top documents should be those favored by multiple retrievers"
    assert len(fused) == 4, "Should contain all unique documents across all lists"
    
    # Verify scores are sorted descending
    scores = [score for _, score in fused]
    assert scores == sorted(scores, reverse=True), "Fused scores must be sorted in descending order"