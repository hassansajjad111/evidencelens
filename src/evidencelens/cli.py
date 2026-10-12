# src/evidencelens/cli.py
import asyncio
from pathlib import Path
import typer
from elasticsearch import AsyncElasticsearch
from qdrant_client import AsyncQdrantClient

from evidencelens.config import get_settings
from evidencelens.index.es import INDEX as ES_INDEX, SETTINGS as ES_SETTINGS, MAPPINGS as ES_MAPPINGS
from evidencelens.index.qdrant import create_collection_if_not_exists
from evidencelens.ingest.loader import index_pubmed_file

app = typer.Typer(help="EvidenceLens Management CLI")
settings = get_settings()

@app.command("init-indices")
def init_indices():
    """Initializes Elasticsearch indices and Qdrant collections."""
    async def _run():
        es = AsyncElasticsearch(settings.es_url, basic_auth=(settings.es_user, settings.es_password))
        qc = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        
        # 1. Create Elasticsearch index with custom biomedical mappings
        if not await es.indices.exists(index=ES_INDEX):
            await es.indices.create(index=ES_INDEX, settings=ES_SETTINGS, mappings=ES_MAPPINGS)
            print(f"Created Elasticsearch index: {ES_INDEX}")
        else:
            print(f"Elasticsearch index {ES_INDEX} already exists.")
            
        # 2. Create Qdrant collection with payload indexes
        await create_collection_if_not_exists(qc)
        print("Qdrant collection and payload indexes verified/created.")
        
        await es.close()
        await qc.close()

    asyncio.run(_run())

@app.command("ingest")
def ingest(xml_path: Path = typer.Argument(..., help="Path to compressed PubMed XML file (.xml.gz)")):
    """Ingests a PubMed XML file into Elasticsearch and Qdrant."""
    async def _run():
        es = AsyncElasticsearch(settings.es_url, basic_auth=(settings.es_user, settings.es_password))
        qc = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        
        await index_pubmed_file(xml_path, es, qc)
        
        await es.close()
        await qc.close()

    asyncio.run(_run())

if __name__ == "__main__":
    app()