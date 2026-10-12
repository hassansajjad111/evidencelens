# src/evidencelens/ingest/loader.py
import asyncio
from pathlib import Path
from elasticsearch import AsyncElasticsearch
from qdrant_client import AsyncQdrantClient
from qdrant_client import models
from sentence_transformers import SentenceTransformer

from evidencelens.ingest.pubmed import parse_file
from evidencelens.index.es import INDEX as ES_INDEX
from evidencelens.index.qdrant import COLLECTION as QDRANT_COLLECTION

_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

async def index_pubmed_file(xml_path: Path, es: AsyncElasticsearch, qc: AsyncQdrantClient, batch_size: int = 50):
    """Parses a compressed PubMed XML file and indexes chunks into Elasticsearch and Qdrant."""
    print(f"Starting ingestion from {xml_path}...")
    
    es_buffer = []
    qdrant_points = []
    count = 0

    for record in parse_file(xml_path):
        if record["op"] != "upsert":
            continue
            
        pmid = record["pmid"]
        title = record["title"]
        abstract = record["abstract"]
        year = record["year"]
        mesh = record["mesh"]
        
        if not abstract:
            continue

        chunk_id = f"pmid_{pmid}_ch0"
        
        # 1. Prepare Elasticsearch doc
        es_buffer.append({"index": {"_index": ES_INDEX, "_id": chunk_id}})
        es_buffer.append({
            "chunk_id": chunk_id,
            "doc_id": pmid,
            "source": "pubmed",
            "section": "abstract",
            "title": title,
            "text": abstract,
            "year": year,
            "pub_types": [],
            "mesh": mesh,
            "license": "open",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })

        # 2. Prepare Qdrant vector point
        vector = _model.encode(f"{title} {abstract}", normalize_embeddings=True).tolist()
        qdrant_points.append(
            models.PointStruct(
                id=abs(hash(chunk_id)) % (2**63),  # Numeric ID hash for Qdrant
                vector={"dense": vector},
                payload={
                    "chunk_id": chunk_id,
                    "doc_id": pmid,
                    "source": "pubmed",
                    "year": year or 2023,
                    "mesh": mesh
                }
            )
        )

        count += 1
        
        # Flush batches when limit is reached
        if len(es_buffer) >= batch_size * 2:
            await _flush_batches(es, qc, es_buffer, qdrant_points)
            es_buffer.clear()
            qdrant_points.clear()
            print(f"Indexed {count} records so far...")

    # Flush any remaining items
    if es_buffer:
        await _flush_batches(es, qc, es_buffer, qdrant_points)
        
    print(f"Ingestion complete! Total indexed: {count} records.")

async def _flush_batches(es: AsyncElasticsearch, qc: AsyncQdrantClient, es_buf: list, qdrant_pts: list):
    """Helper to bulk upload to Elasticsearch and upsert to Qdrant."""
    if es_buf:
        await es.bulk(body=es_buf)
    if qdrant_pts:
        await qc.upsert(collection_name=QDRANT_COLLECTION, points=qdrant_pts)