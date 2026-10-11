# src/evidencelens/index/qdrant.py
from qdrant_client import AsyncQdrantClient, models

COLLECTION = "el_chunks_v1"

async def init_qdrant(qdrant_url: str, api_key: str | None = None) -> AsyncQdrantClient:
    """Initializes and verifies the Qdrant async client."""
    qc = AsyncQdrantClient(url=qdrant_url, api_key=api_key)
    # Verify connectivity
    await qc.get_collections()
    return qc

async def create_collection_if_not_exists(qc: AsyncQdrantClient, dim: int = 384):
    """Creates the Qdrant collection with named dense + sparse vectors and payload indexes."""
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
       
        # Create payload indexes BEFORE bulk load (critical for performance)[cite: 2, 3]
        for field, schema in [
            ("year", models.PayloadSchemaType.INTEGER), 
            ("source", models.PayloadSchemaType.KEYWORD),
            ("pub_types", models.PayloadSchemaType.KEYWORD), 
            ("mesh", models.PayloadSchemaType.KEYWORD),
            ("license", models.PayloadSchemaType.KEYWORD)
        ]:
            await qc.create_payload_index(COLLECTION, field_name=field, field_schema=schema)