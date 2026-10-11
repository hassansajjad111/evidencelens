# src/evidencelens/index/qdrant.py
"""Qdrant collection setup for the project's vector retrieval store.

Dense vectors use cosine distance, while a named sparse vector is reserved for
the planned sparse/hybrid path. Payload indexes support filters such as year and
source. This module creates schema only; document embeddings and point upserts
are not implemented in the current ingestion flow.
"""

from qdrant_client import AsyncQdrantClient, models

# Must stay aligned with Qdrant search and any future index/rebuild command.
COLLECTION = "el_chunks_v1"


async def init_qdrant(qdrant_url: str, api_key: str | None = None) -> AsyncQdrantClient:
    """Create a Qdrant client and verify server connectivity before returning it."""
    qc = AsyncQdrantClient(url=qdrant_url, api_key=api_key)
    # Verify connectivity
    await qc.get_collections()
    return qc

async def create_collection_if_not_exists(qc: AsyncQdrantClient, dim: int = 384):
    """Idempotently create dense/sparse vector schema and prefilter payload indexes.

    `dim` must exactly match the embedding model used for every query and point.
    Creating indexes before a bulk load keeps filtered-search setup predictable.
    """
    collections = await qc.get_collections()
    exists = any(c.name == COLLECTION for c in collections.collections)
    
    if not exists:
        await qc.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": models.VectorParams(
                    size=dim, 
                    distance=models.Distance.COSINE,
                    hnsw_config=models.HnswConfigDiff(m=16, ef_construct=128)
                )
            },
            sparse_vectors_config={
                "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
       
        # Create payload indexes before loading points so filter fields are indexed.
        for field, schema in [
            ("year", models.PayloadSchemaType.INTEGER), 
            ("source", models.PayloadSchemaType.KEYWORD),
            ("pub_types", models.PayloadSchemaType.KEYWORD), 
            ("mesh", models.PayloadSchemaType.KEYWORD),
            ("license", models.PayloadSchemaType.KEYWORD)
        ]:
            await qc.create_payload_index(COLLECTION, field_name=field, field_schema=schema)