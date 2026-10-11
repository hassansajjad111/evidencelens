# src/evidencelens/retrieval/dense.py
from qdrant_client import AsyncQdrantClient
from qdrant_client import models
from sentence_transformers import SentenceTransformer
from evidencelens.index.qdrant import COLLECTION

# Initialize lightweight CPU-optimized embedding model for your 8GB RAM MacBook
_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

async def search_dense(qc: AsyncQdrantClient, query: str, k: int = 10, year_min: int | None = None) -> list[str]:
    """
    Performs dense semantic vector search on Qdrant using BAAI/bge-small-en-v1.5 embeddings.
    Returns a list of matching chunk IDs sorted by cosine similarity score.
    """
    # Encode query text into a 384-dimensional dense vector
    query_vector = _model.encode(query, normalize_embeddings=True).tolist()
    
    # Optional payload filter for year
    query_filter = None
    if year_min is not None:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="year", range=models.Range(gte=year_min))]
        )
        
    hits = await qc.search(
        collection_name=COLLECTION,
        query_vector=("dense", query_vector),
        query_filter=query_filter,
        limit=k
    )
    
    # Extract chunk IDs from point payloads
    return [str(hit.payload.get("chunk_id")) for hit in hits if hit.payload]