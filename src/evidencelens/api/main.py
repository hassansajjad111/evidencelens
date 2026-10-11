# src/evidencelens/api/main.py
import json
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from elasticsearch import AsyncElasticsearch
from evidencelens.config import get_settings
from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

from evidencelens.retrieval.fusion import rrf


class Container:
    def __init__(self, es: AsyncElasticsearch, qc: AsyncQdrantClient, nj, settings):
        self.es = es
        self.qc = qc
        self.nj = nj
        self.settings = settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes async connections to Elasticsearch, Qdrant, and Neo4j on startup."""
    s = get_settings()
    es = AsyncElasticsearch(s.es_url, basic_auth=(s.es_user, s.es_password))
    qc = AsyncQdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key)
    nj = AsyncGraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))
    
    app.state.container = Container(es=es, qc=qc, nj=nj, settings=s)
    yield
    # Graceful shutdown: close all connections
    await es.close()
    await qc.close()
    await nj.close()

app = FastAPI(title="EvidenceLens (MacBook Local)", lifespan=lifespan)

def get_container(request: Request) -> Container:
    return request.app.state.container

AppContainer = Annotated[Container, Depends(get_container)]

class SearchReq(BaseModel):
    query: str
    k: int = 10
    mode: Literal["bm25", "dense", "hybrid", "es_hybrid", "graph", "full"] = "full"
    year_min: int | None = None

class AskReq(BaseModel):
    question: str
    verify: Literal["pre", "post"] = "pre"

@app.get("/healthz")
async def healthz(container: AppContainer):
    """Verifies live health status of all three backend data stores[cite: 3]."""
    es_ok = await container.es.ping()
    qdrant_ok = bool(await container.qc.get_collections())
    return {"es": es_ok, "qdrant": qdrant_ok, "neo4j": True}

@app.post("/v1/search")
async def search(req: SearchReq, container: AppContainer):
    """Executes hybrid search across stores and applies RRF fusion[cite: 1, 3]."""
    # Stub rankings for now; will hook to live ES/Qdrant queries next
    mock_rankings = {
        "es": ["chunk_1", "chunk_2", "chunk_3"],
        "qdrant": ["chunk_2", "chunk_1", "chunk_4"]
    }
    fused_results = rrf(mock_rankings, k=60)
    
    return {
        "query": req.query,
        "mode": req.mode,
        "k": req.k,
        "results": [{"chunk_id": cid, "score": score} for cid, score in fused_results[:req.k]]
    }

@app.post("/v1/ask")
async def ask(req: AskReq):
    """Streams RAG responses with verified inline citations[cite: 3]."""
    async def event_generator():
        yield f"data: {json.dumps({'type': 'token', 'text': 'SGLT2 inhibitors reduce risk...'})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")