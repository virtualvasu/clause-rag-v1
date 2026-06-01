"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    All configuration loaded from .env file.
    Type hints enforce validation at startup.
    Missing required vars raise ValueError immediately.
    """

    # === LLM APIs ===
    anthropic_api_key: Optional[str] = None   # Required if enrichment_provider=claude
    openai_api_key: Optional[str] = None      # Required for embeddings (Step 4)
    cohere_api_key: Optional[str] = None
    langsmith_api_key: Optional[str] = None

    # === Ollama (local, free — alternative to Claude for enrichment) ===
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:7b"          # Any model pulled via `ollama pull`

    # === Enrichment Provider ===
    # "claude"  → uses anthropic_api_key + contextualization_model (cloud, ~$1-2)
    # "ollama"  → uses ollama_base_url + ollama_model (local, free)
    enrichment_provider: str = "ollama"

    # === Qdrant (Vector DB) ===
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "clause_chunks"

    # === Neo4j (Graph DB) ===
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str

    # === Models (Locked — do not change) ===
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072
    generation_model: str = "claude-sonnet-4-20250514"
    contextualization_model: str = "claude-haiku-20240307"

    # === Retrieval Parameters (Tunable) ===
    top_k_retrieval: int = 20
    top_k_rerank: int = 5
    max_agent_iterations: int = 3

    # === Chunking Parameters (Locked) ===
    child_chunk_size: int = 256
    parent_chunk_size: int = 1024
    child_chunk_overlap: int = 20

    # === Observability (Optional) ===
    langsmith_project: Optional[str] = None
    langchain_tracing_v2: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields


# Single instance — imported across codebase
settings = Settings()
