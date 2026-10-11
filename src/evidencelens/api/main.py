# src/evidencelens/api/main.py
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from elasticsearch import AsyncElasticsearch
from fastapi import Depends, FastAPI, HTTPException, Request
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

from evidencelens.config import get_settings
from evidencelens.retrieval.dense import search_dense
from evidencelens.retrieval.fusion import rrf
from evidencelens.retrieval.lexical import search_lexical


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
    mode: Literal["bm25", "dense", "hybrid"] = "hybrid"
    year_min: int | None = None

class AskReq(BaseModel):
    question: str
    verify: Literal["pre", "post"] = "pre"

@app.get("/healthz")
async def healthz(container: AppContainer):
    """Checks connectivity to all configured data stores."""
    try:
        es_ok = bool(await container.es.ping())
    except Exception:  # noqa: BLE001 - report backend outages as degraded health.
        es_ok = False

    try:
        await container.qc.get_collections()
        qdrant_ok = True
    except Exception:  # noqa: BLE001 - report backend outages as degraded health.
        qdrant_ok = False

    try:
        await container.nj.verify_connectivity()
        neo4j_ok = True
    except Exception:  # noqa: BLE001 - report backend outages as degraded health.
        neo4j_ok = False

    return {
        "status": "ok" if es_ok and qdrant_ok and neo4j_ok else "degraded",
        "es": es_ok,
        "qdrant": qdrant_ok,
        "neo4j": neo4j_ok,
    }

@app.post("/v1/search")
async def search(req: SearchReq, container: AppContainer):
    """Runs the selected implemented retriever or fuses lexical and dense results."""
    rankings: dict[str, list[str]] = {}
    if req.mode in ("bm25", "hybrid"):
        rankings["es"] = await search_lexical(
            container.es, req.query, k=req.k, year_min=req.year_min
        )
    if req.mode in ("dense", "hybrid"):
        rankings["qdrant"] = await search_dense(
            container.qc,
            req.query,
            k=req.k,
            year_min=req.year_min,
            model_name=container.settings.embed_model,
        )

    fused_results = rrf(rankings, k=60)
    
    return {
        "query": req.query,
        "mode": req.mode,
        "k": req.k,
        "results": [{"chunk_id": cid, "score": score} for cid, score in fused_results[:req.k]]
    }

@app.post("/v1/ask")
async def ask(req: AskReq):
    """RAG generation is not implemented; never return fabricated evidence."""
    raise HTTPException(
        status_code=501,
        detail="Grounded answer generation is not implemented yet; use /v1/search.",
    )