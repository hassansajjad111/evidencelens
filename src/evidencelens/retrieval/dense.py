"""`src/evidencelens/retrieval/dense.py`: Qdrant retrieval with lazy embeddings.

The model is cached per process and loaded only when dense search is first used,
so BM25-only workflows do not pay model startup or memory costs. Encoding runs
in a worker thread to avoid blocking the FastAPI event loop. A matching Qdrant
collection, model, and vector dimension must already be provisioned.
"""

import asyncio
from functools import lru_cache

from qdrant_client import AsyncQdrantClient, models

from evidencelens.index.qdrant import COLLECTION


@lru_cache(maxsize=2)
def _get_model(model_name: str):
    """Load each selected sentence-transformers model once per process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _encode_query(model_name: str, query: str) -> list[float]:
    """Create one normalized query vector; normalized vectors suit cosine search."""
    return _get_model(model_name).encode(query, normalize_embeddings=True).tolist()


async def search_dense(
    qc: AsyncQdrantClient,
    query: str,
    k: int = 10,
    year_min: int | None = None,
    model_name: str = "BAAI/bge-small-en-v1.5",
) -> list[str]:
    """Return ranked chunk IDs from Qdrant, optionally filtered to a minimum year.

    The caller supplies the model name so the query encoder can match configured
    model selection; the indexed vectors must have been created with that model.
    """
    query_vector = await asyncio.to_thread(_encode_query, model_name, query)
    
    query_filter = None
    if year_min is not None:
        # Apply the year condition inside Qdrant rather than discarding top hits later.
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