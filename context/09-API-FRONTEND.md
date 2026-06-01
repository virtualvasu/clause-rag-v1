# 09 — API & Frontend

Covers Steps 11-12: FastAPI service layer and Streamlit demo UI.

---

## FastAPI Service

**File**: `clause/api/main.py`

Async HTTP API for query and ingestion.

### Endpoints

#### POST /query

Query the RAG system and get a legal answer with citations.

**Request:**
```json
{
  "query": "What are the audit requirements for a small startup?",
  "mode": "auto"
}
```

**Response:**
```json
{
  "answer": "Under Section 138 of the Companies Act 2013, a small company is exempt from mandatory audit unless...",
  "citations": [
    {
      "act": "Companies Act 2013",
      "section_type": "Section",
      "section_number": "138",
      "section_title": "Exemption from compliance with accounting standards",
      "chunk_id": "CA2013_S138_1"
    }
  ],
  "query_type": "CONDITIONAL",
  "iterations": 2,
  "context_chunks_used": 5,
  "graph_nodes_used": 3
}
```

#### POST /ingest

Trigger the full ingestion pipeline on new documents.

**Request:**
```json
{
  "source_dir": "data/raw/",
  "doc_metadata": {
    "dpiit_guidelines": {
      "year": 2024,
      "version": "3.0"
    }
  }
}
```

**Response:**
```json
{
  "chunks_created": 12450,
  "nodes_created": 1240,
  "edges_created": 3890,
  "duration_seconds": 342.5
}
```

#### GET /health

Service health check.

**Response:**
```json
{
  "qdrant": "ok",
  "neo4j": "ok",
  "openai": "ok",
  "anthropic": "ok",
  "status": "ready"
}
```

#### GET /graph/stats

Graph database statistics.

**Response:**
```json
{
  "nodes": 1240,
  "edges": 3890,
  "acts": ["Companies Act 2013", "SEBI ICDR 2018", ...],
  "total_sections": 456,
  "total_obligations": 89,
  "total_penalties": 145
}
```

---

## Request/Response Schemas

**File**: `clause/api/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional

class QueryRequest(BaseModel):
    query: str = Field(..., description="Legal question")
    mode: str = Field(default="auto", description="auto | simple | full")

class Citation(BaseModel):
    act: str
    section_type: str  # "Section" | "Rule" | "Regulation"
    section_number: str
    section_title: Optional[str] = None
    chunk_id: Optional[str] = None
    text_excerpt: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    query_type: str  # "SIMPLE" | "MULTI_HOP" | "CROSS_DOC" | "CONDITIONAL"
    iterations: int  # How many CRAG iterations
    context_chunks_used: int
    graph_nodes_used: int

class IngestRequest(BaseModel):
    source_dir: str
    doc_metadata: dict = Field(default_factory=dict)

class IngestResponse(BaseModel):
    chunks_created: int
    nodes_created: int
    edges_created: int
    duration_seconds: float

class HealthResponse(BaseModel):
    qdrant: str  # "ok" | "error"
    neo4j: str
    openai: str
    anthropic: str
    status: str  # "ready" | "degraded" | "error"
```

---

## App Factory

```python
# clause/api/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

def create_app() -> FastAPI:
    """
    FastAPI application factory with middleware and routes.
    """
    app = FastAPI(
        title="Clause API",
        description="Legal Q&A for Indian startups",
        version="1.0.0",
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Logging
    logging.basicConfig(level=logging.INFO)
    
    # Routes
    from clause.api.routes import query_routes, ingest_routes
    app.include_router(query_routes.router)
    app.include_router(ingest_routes.router)
    
    return app

app = create_app()
```

**Run locally:**
```bash
uvicorn clause.api.main:app --reload --port 8000
```

Docs available at `http://localhost:8000/docs` (Swagger UI).

---

## Streamlit Frontend

**File**: `frontend/app.py`

Demo UI for interactive query and result exploration.

```python
import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="⚖️ Clause", layout="wide")

st.title("⚖️ Clause — Legal AI for Indian Startups")
st.markdown("""
Legal clarity for startup founders, CAs, and compliance officers.
""")

# Query input
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("Ask a legal question:", placeholder="e.g., What are audit requirements for a small company?")
with col2:
    mode = st.selectbox("Mode", ["auto", "simple", "full"])

if st.button("Ask", use_container_width=True):
    with st.spinner("Processing..."):
        response = requests.post(
            "http://localhost:8000/query",
            json={"query": query, "mode": mode}
        )
        result = response.json()
    
    # Answer section
    st.markdown("---")
    st.subheader("Answer")
    st.markdown(result["answer"])
    
    # Metadata
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Query Type", result["query_type"])
    with col2:
        st.metric("Iterations", result["iterations"])
    with col3:
        st.metric("Chunks Used", result["context_chunks_used"])
    with col4:
        st.metric("Graph Nodes", result["graph_nodes_used"])
    
    st.markdown("---")
    
    # Citations
    st.subheader("Citations")
    for i, citation in enumerate(result["citations"], 1):
        with st.expander(f"{i}. {citation['act']}, {citation['section_type']} {citation['section_number']}"):
            if citation.get("section_title"):
                st.write(f"**Title:** {citation['section_title']}")
            if citation.get("text_excerpt"):
                st.write(f"**Text:** {citation['text_excerpt']}...")
    
    # Retrieved context (collapsible)
    with st.expander("View Retrieved Context"):
        st.write("Context chunks sent to LLM for generation")
        # Display context chunks

# Sidebar
with st.sidebar:
    st.header("About")
    st.write("""
    **Clause** is a GraphRAG system specialized in Indian corporate and startup law.
    
    - **Corpus:** Companies Act 2013, MCA Rules, SEBI Regulations, DPIIT Guidelines
    - **Architecture:** Hierarchical chunking + hybrid retrieval + knowledge graph + agentic loop
    - **Evaluation:** RAGAS-based quality metrics
    """)
    
    if st.button("Health Check"):
        health = requests.get("http://localhost:8000/health").json()
        st.json(health)
```

**Run:**
```bash
streamlit run frontend/app.py
```

**Access:** `http://localhost:8501`

---

## UI Components

```
┌──────────────────────────────────────────────────────────┐
│  ⚖️  Clause — Legal AI for Indian Startups              │
├──────────────────────────────────────────────────────────┤
│  [Query Input Field]                        [Dropdown]   │
│  [Ask Button]                                            │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Answer:                                                 │
│  "Under Section 42 of the Companies Act 2013, a company │
│   must not issue fresh offers within 60 days of a       │
│   private placement [Companies Act 2013, Section 42]..." │
│                                                           │
│  ──────────────────────────────────────────────────────  │
│  Query Type: CROSS_DOC  │ Iterations: 2 │ Chunks: 5    │
│                                                           │
│  ──────────────────────────────────────────────────────  │
│  Citations:                                              │
│  > 1. Companies Act 2013, Section 42                    │
│  > 2. SEBI ICDR 2018, Regulation 26                     │
│                                                           │
│  ────────────── View Retrieved Context ────────────────  │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

Key UI features:
- **Query metadata display** — Shows query type and iteration count (demonstrates intelligence)
- **Expandable citations** — Click to see full section text
- **Retrievable context** — Show what was sent to LLM
- **Health dashboard** — Monitor services in sidebar

---

## Deployment

### Local Development
```bash
# Terminal 1: Services
docker-compose up -d

# Terminal 2: API
uvicorn clause.api.main:app --reload

# Terminal 3: Frontend
streamlit run frontend/app.py
```

### Production (Docker)
```bash
docker build -t clause-api .
docker run -p 8000:8000 clause-api
```

---

## 🔗 Next Steps

- Data models: [10-DATA-MODELS.md](10-DATA-MODELS.md)
- Graph schema: [11-GRAPH-SCHEMA.md](11-GRAPH-SCHEMA.md)
