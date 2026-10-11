"""`src/evidencelens/index/es.py`: ES schema and async connectivity helper.

The schema defines biomedical-aware text analysis and exact-match metadata fields.
Elasticsearch is the lexical/BM25 engine and source for later chunk hydration;
actual index creation and bulk ingestion are not wired into the current pipeline.
"""

from elasticsearch import AsyncElasticsearch

# Keep this index name coordinated with retrieval, ingestion, and rebuild scripts.
INDEX = "el_chunks_v1"
# Preserve common biomedical tokens so analyzer splitting does not destroy them.
PROTECTED = ["HbA1c", "IL-6", "T2DM", "SGLT2", "GLP-1", "eGFR", "LDL-C", "NT-proBNP"]

# Small single-node settings suit local development; not a production cluster plan.
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

# Strict mappings catch accidental field drift between parsers and index writers.
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

async def init_elasticsearch(es_url: str, api_key: str | None = None) -> AsyncElasticsearch:
    """Create and ping an async ES client; authentication is configured by callers.

    `api_key` is retained as a future integration point and is not currently used.
    """
    es = AsyncElasticsearch(es_url)
    if not await es.ping():
        raise ConnectionError(f"Could not connect to Elasticsearch at {es_url}")
    return es