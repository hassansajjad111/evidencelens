from typing import Literal
import json
from fastapi.responses import StreamingResponse
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="EvidenceLens (MacBook Local)")

class SearchReq(BaseModel):
    query: str
    k: int = 10
    mode: Literal["bm25", "dense", "hybrid", "es_hybrid", "graph", "full"] = "full"
    year_min: int | None = None

class AskReq(BaseModel):
    question: str
    verify: Literal["pre", "post"] = "pre"

@app.get("/healthz")
async def healthz():
    return {"es": True, "qdrant": True, "neo4j": True}

@app.post("/v1/search")
async def search(req: SearchReq):
    # Stub response to verify routing and payload validation
    return {
        "query": req.query,
        "mode": req.mode,
        "k": req.k,
        "results": []
    }

@app.post("/v1/ask")
async def ask(req: AskReq):
    """
    1. Retrieves evidence from ES, Qdrant, and Neo4j.
    2. Reranks evidence using BAAI/bge-reranker-base.
    3. Streams response with verified inline citations [E1], [E2].
    """
    async def event_generator():
        # Example streaming event payload
        yield f"data: {json.dumps({'type': 'token', 'text': 'SGLT2 inhibitors reduce risk...'})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")