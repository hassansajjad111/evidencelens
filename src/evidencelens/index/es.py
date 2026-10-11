# src/evidencelens/index/es.py
from elasticsearch import AsyncElasticsearch

INDEX = "el_chunks_v1"
PROTECTED = ["HbA1c", "IL-6", "T2DM", "SGLT2", "GLP-1", "eGFR", "LDL-C", "NT-proBNP"]

SETTINGS = {
    "number_of_shards": 1, 
    "number_of_replicas": 0,
    "analysis": {
        "filter": {
            "bio_wdg": {
                "type": "word_delimiter_graph", 
                "protected_words": PROTECTED,
                "split_on_numerics": False, 
                "split_on_case_change": False, 
                "preserve_original": True
            },
            "en_stem": {"type": "stemmer", "language": "light_english"},
        },
        "analyzer": {
            "bio_index": {
                "tokenizer": "whitespace", 
                "filter": ["bio_wdg", "lowercase", "flatten_graph", "en_stem"]
            },
            "bio_search": {
                "tokenizer": "whitespace", 
                "filter": ["bio_wdg", "lowercase", "en_stem"]
            },
        },
    },
}

MAPPINGS = {
    "dynamic": "strict", 
    "properties": {
        "chunk_id": {"type": "keyword"}, 
        "doc_id": {"type": "keyword"},
        "source": {"type": "keyword"}, 
        "section": {"type": "keyword"},
        "title": {"type": "text", "analyzer": "bio_index", "search_analyzer": "bio_search"},
        "text": {"type": "text", "analyzer": "bio_index", "search_analyzer": "bio_search"},
        "year": {"type": "short"}, 
        "pub_types": {"type": "keyword"}, 
        "mesh": {"type": "keyword"},
        "license": {"type": "keyword"}, 
        "url": {"type": "keyword", "index": False},
    }
}

async def init_elasticsearch(es_url: str, api_key: str = None) -> AsyncElasticsearch:
    """Initializes and verifies the Elasticsearch async client."""
    es = AsyncElasticsearch(es_url)
    if not await es.ping():
        raise ConnectionError(f"Could not connect to Elasticsearch at {es_url}")
    return es