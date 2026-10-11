"""`src/evidencelens/retrieval/lexical.py`: BM25 retrieval over title and body.

The title is boosted above the body, and an optional year lower bound is sent
as a non-scoring filter. The result contract is a ranked list of shared chunk
IDs so lexical and dense candidates can be fused independently of raw scores.
"""

from typing import Any, cast

from elasticsearch import AsyncElasticsearch

from evidencelens.index.es import INDEX


async def search_lexical(es: AsyncElasticsearch, query: str, k: int = 10, year_min: int | None = None) -> list[str]:
    """Search the ES index and return hit chunk IDs in BM25 relevance order."""
    body: dict[str, Any] = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^2", "text"],
                            "analyzer": "bio_search"
                        }
                    }
                ]
            }
        },
        "size": k
    }
    
    if year_min is not None:
        # Filters constrain eligible documents but do not alter BM25 relevance scores.
        body["query"]["bool"]["filter"] = [{"range": {"year": {"gte": year_min}}}]
        
    resp = await es.search(index=INDEX, body=body)
    hits = resp.get("hits", {}).get("hits", [])
    
    chunk_ids: list[str] = []
    for hit in hits:
        hit_dict = cast(dict[str, Any], hit)
        source = hit_dict.get("_source")
        if isinstance(source, dict) and "chunk_id" in source:
            chunk_ids.append(str(source["chunk_id"]))
    return chunk_ids