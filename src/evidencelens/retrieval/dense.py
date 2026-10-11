# src/evidencelens/retrieval/dense.py
from qdrant_client import AsyncQdrantClient, models
from sentence_transformers import SentenceTransformer

from evidencelens.index.qdrant import COLLECTION

_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

async def search_dense(qc: AsyncQdrantClient, query: str, k: int = 10, year_min: int | None = None) -> list[str]:
    """
    Performs dense semantic vector search on Qdrant using BAAI/bge-small-en-v1.5 embeddings.
    Returns a list of matching chunk IDs sorted by cosine similarity score.
    """
    query_vector = _model.encode(query, normalize_embeddings=True).tolist()
    
    query_filter = None
    if year_min is not None:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="year", range=models.Range(gte=year_min))]
        )
        
    response = await qc.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        using="dense",
        query_filter=query_filter,
        limit=k
    )
    
    chunk_ids: list[str] = []
    for point in response.points:
        payload = point.payload
        if isinstance(payload, dict) and "chunk_id" in payload:
            chunk_ids.append(str(payload["chunk_id"]))
    return chunk_ids