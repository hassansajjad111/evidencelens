# src/evidencelens/retrieval/lexical.py
from elasticsearch import AsyncElasticsearch
from evidencelens.index.es import INDEX

async def search_lexical(es: AsyncElasticsearch, query: str, k: int = 10, year_min: int | None = None) -> list[str]:
    """
    Performs BM25 lexical search on Elasticsearch using the custom biomedical analyzer.
    Returns a list of matching chunk IDs sorted by relevance score.
    """
    body = {
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
    
    # Optional year filter if specified in the request
    if year_min is not None:
        body["query"]["bool"]["filter"] = [{"range": {"year": {"gte": year_min}}}]
        
    resp = await es.search(index=INDEX, body=body)
    hits = resp["hits"]["hits"]
    
    # Extract and return the chunk IDs from the search hits
    return [hit["_source"]["chunk_id"] for hit in hits]