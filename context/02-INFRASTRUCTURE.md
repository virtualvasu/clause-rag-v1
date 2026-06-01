# 02 — Infrastructure & Environment Setup

## Overview

This section covers all infrastructure setup needed before implementing the system: Docker services, environment variables, and configuration management.

---

## docker-compose.yml

Run Qdrant and Neo4j locally. API runs outside Docker during development.

```yaml
version: "3.8"

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"   # Browser UI
      - "7687:7687"   # Bolt protocol
    environment:
      NEO4J_AUTH: neo4j/clausepassword
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
    restart: unless-stopped

volumes:
  qdrant_data:
  neo4j_data:
```

### Startup Commands

```bash
# Start services
docker-compose up -d

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f qdrant
docker-compose logs -f neo4j

# Stop services
docker-compose down

# Preserve data when stopping
docker-compose stop
```

### Accessing Services

| Service | URL | Purpose |
|---------|-----|---------|
| Qdrant | `http://localhost:6333` | Vector database API |
| Qdrant Dashboard | `http://localhost:6333/dashboard` | Visualize collections |
| Neo4j Browser | `http://localhost:7474` | Query Cypher, visualize graph |
| Neo4j Bolt | `bolt://localhost:7687` | Python driver connection |

---

## .env.example

Copy this to `.env` and fill in actual values. **Never commit .env to git.**

```bash
# === LLM APIs ===
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# === Vector Database ===
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=clause_chunks

# === Graph Database ===
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=clausepassword

# === Reranker API ===
COHERE_API_KEY=...

# === Observability ===
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=clause
LANGCHAIN_TRACING_V2=true

# === Model Configuration ===
# Do not change without updating ARCHITECTURE.md
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=3072
GENERATION_MODEL=claude-sonnet-4-20250514
CONTEXTUALIZATION_MODEL=claude-haiku-20240307

# === Retrieval Parameters ===
TOP_K_RETRIEVAL=20
TOP_K_RERANK=5
MAX_AGENT_ITERATIONS=3

# === Chunking Parameters ===
CHILD_CHUNK_SIZE=256
PARENT_CHUNK_SIZE=1024
CHILD_CHUNK_OVERLAP=20
```

### Environment Variable Groups

**LLM APIs (Required for all operations)**
- `ANTHROPIC_API_KEY` — Claude generation + enrichment
- `OPENAI_API_KEY` — Embeddings (text-embedding-3-large)

**Qdrant (Required for retrieval)**
- `QDRANT_URL` — Connect to Qdrant service (localhost for dev, cloud for prod)
- `QDRANT_COLLECTION_NAME` — Vector collection name

**Neo4j (Required for graph operations)**
- `NEO4J_URI` — Bolt connection string
- `NEO4J_USERNAME` & `NEO4J_PASSWORD` — Credentials (must match docker-compose.yml)

**Cohere (Required for reranking)**
- `COHERE_API_KEY` — Rerank v3 API key

**LangSmith (Optional, for observability)**
- `LANGSMITH_API_KEY` — Tracing & debugging (can be empty)
- `LANGSMITH_PROJECT` — Project name for filtering
- `LANGCHAIN_TRACING_V2` — Set to true to enable

**Model Config (Locked — do not change)**
- `EMBEDDING_MODEL` — Always `text-embedding-3-large`
- `EMBEDDING_DIMENSIONS` — Always `3072`
- `GENERATION_MODEL` — Always `claude-sonnet-4-20250514`
- `CONTEXTUALIZATION_MODEL` — Always `claude-haiku-20240307`

**Retrieval Config (Tunable)**
- `TOP_K_RETRIEVAL` — Top-K documents for hybrid retrieval (default: 20)
- `TOP_K_RERANK` — Top-K after reranking (default: 5)
- `MAX_AGENT_ITERATIONS` — Max retries in CRAG loop (default: 3)

**Chunking Config (Locked — do not change)**
- `CHILD_CHUNK_SIZE` — Tokens per child chunk (default: 256)
- `PARENT_CHUNK_SIZE` — Tokens per parent chunk (default: 1024)
- `CHILD_CHUNK_OVERLAP` — Overlap in tokens (default: 20)

---

## clause/config.py

Type-safe environment variable management using Pydantic Settings.

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    All configuration loaded from .env file.
    Type hints enforce validation at startup.
    Missing required vars raise ValueError immediately.
    """
    
    # === LLM APIs ===
    anthropic_api_key: str
    openai_api_key: str
    cohere_api_key: str
    langsmith_api_key: Optional[str] = None

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

    class Config:
        env_file = ".env"
        case_sensitive = False

# Single instance — imported across codebase
settings = Settings()
```

### Usage in Code

```python
from clause.config import settings

# In any module:
qdrant_client = QdrantClient(url=settings.qdrant_url)
claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)

# Access any setting
print(settings.embedding_model)  # "text-embedding-3-large"
print(settings.top_k_retrieval)  # 20
```

---

## Local Development Setup Checklist

- [ ] Clone repository
- [ ] `cp .env.example .env` — Create .env file
- [ ] Fill in API keys in .env
  - [ ] ANTHROPIC_API_KEY
  - [ ] OPENAI_API_KEY
  - [ ] COHERE_API_KEY
- [ ] `docker-compose up -d` — Start Qdrant + Neo4j
- [ ] Verify containers running: `docker ps`
- [ ] Test Qdrant: `curl http://localhost:6333/health`
- [ ] Test Neo4j: `curl http://localhost:7474` (should redirect)
- [ ] `pip install -r requirements.txt` — Install Python deps
- [ ] `python -m pytest tests/` — Run tests to verify setup

---

## Production Deployment Notes

**Qdrant in Production:**
- Use Qdrant cloud service instead of local Docker
- Set `QDRANT_URL` to cloud endpoint
- Use API key authentication if available

**Neo4j in Production:**
- Use Neo4j AuraDB or self-managed enterprise instance
- Update `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
- Consider APOC plugin for advanced queries

**API Key Rotation:**
- Use AWS Secrets Manager, HashiCorp Vault, or similar
- Never hardcode secrets
- Rotate API keys on schedule

---

## 🔗 Next Steps

- Understand parsing: [03-INGESTION-PIPELINE.md](03-INGESTION-PIPELINE.md)
- View full architecture: [01-PROJECT-OVERVIEW.md](01-PROJECT-OVERVIEW.md)
