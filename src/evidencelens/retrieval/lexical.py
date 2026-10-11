# src/evidencelens/retrieval/lexical.py
from typing import Any, cast

from elasticsearch import AsyncElasticsearch

from evidencelens.index.es import INDEX


async def search_lexical(es: AsyncElasticsearch, query: str, k: int = 10, year_min: int | None = None) -> list[str]:
    """
    Performs BM25 lexical search on Elasticsearch using the custom biomedical analyzer.
    Returns a list of matching chunk IDs sorted by relevance score.
    """
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