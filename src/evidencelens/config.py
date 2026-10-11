# src/evidencelens/config.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EL_", env_file=".env", extra="ignore")
    es_url: str = "http://127.0.0.1:9200"
    es_user: str = "elastic"
    es_password: str = "change-me"
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_api_key: str | None = None
    neo4j_uri: str = "bolt://127.0.0.1:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "change-me-too"
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384
    rerank_model: str = "BAAI/bge-reranker-base"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "gemma:2b"
    ncbi_api_key: str | None = None
    openfda_api_key: str | None = None
    contact_email: str = "you@example.com"

@lru_cache
def get_settings() -> Settings:
    return Settings()