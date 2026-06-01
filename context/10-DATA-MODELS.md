# 10 — Data Models (Pydantic)

Complete Pydantic model definitions used throughout the system.

---

## Internal Models

### LegalChunk

**File**: `clause/ingestion/chunkers/section_chunker.py`

```python
from pydantic import BaseModel
from typing import Optional

class LegalChunk(BaseModel):
    """
    Represents a chunk of legal text at any hierarchy level.
    """
    chunk_id: str
    """Deterministic ID. Format: ACT_S{n} or ACT_S{n}_{m}"""
    
    type: str
    """One of: "document", "parent", "child", "table" """
    
    parent_id: Optional[str] = None
    """Only set on child chunks. Points to parent chunk ID."""
    
    act: str
    """e.g. "Companies Act 2013" """
    
    chapter: Optional[str] = None
    """e.g. "Chapter II" """
    
    section_number: Optional[str] = None
    """e.g. "42", "42(3)", "Rule 14" """
    
    section_title: Optional[str] = None
    """e.g. "Private Placements" """
    
    text: str
    """Original text — shown in citations. Never modified."""
    
    contextualized_text: Optional[str] = None
    """Set by enrichment step. Prepends 1-2 context sentences. Used for embedding."""
    
    cross_references: list[str] = []
    """["Section 43", "Rule 14"] — detected by regex. Become graph edges."""
    
    tokens: int
    """Token count of original text. Validated against bounds."""
    
    source_file: str
    """Source PDF or HTML filename."""
    
    sentence_window: Optional[str] = None
    """±2 sentences around child chunk for context."""
```

### ClauseState

**File**: `clause/agent/state.py`

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class ClauseState(TypedDict):
    """
    Immutable state object for LangGraph agent execution.
    Each node receives full state, returns partial updates.
    """
    
    # === Input ===
    original_query: str
    """User's original question."""
    
    query_type: str
    """Classification: SIMPLE | MULTI_HOP | CROSS_DOC | CONDITIONAL """
    
    # === Query Processing ===
    expanded_queries: list[str]
    """Original query + 3 expansions for better recall."""
    
    hyde_text: str
    """Hypothetical document text generated from query."""
    
    # === Retrieval ===
    retrieved_chunks: list[dict]
    """After RRF + reranking. Format: {chunk_id, text, score, source}"""
    
    parent_chunks: list[dict]
    """Parent sections fetched from child chunk IDs."""
    
    graph_context: list[dict]
    """Neo4j traversal results: obligations, penalties, exemptions."""
    
    # === Evaluation ===
    context_score: float
    """CRAG check relevance score (0-1). Threshold: 0.6"""
    
    iteration_count: int
    """Current iteration in CRAG loop. Max: 3"""
    
    refinement_reason: str
    """Why context was insufficient. Guides query refinement."""
    
    # === Generation ===
    final_context: list[dict]
    """Merged vector + graph context sent to LLM."""
    
    answer: str
    """Generated answer text."""
    
    citations: list[dict]
    """Extracted inline citations: [{act, section_number, title, chunk_id}]"""
    
    # === Meta ===
    messages: Annotated[list, add_messages]
    """LangGraph message history (for observability)."""
```

---

## API Models

All API models in **`clause/api/schemas.py`**

### Request Models

```python
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5, description="Legal question")
    mode: str = Field(
        default="auto",
        regex="^(auto|simple|full)$",
        description="Query mode: auto (default), simple (no graph), full (all components)"
    )

class IngestRequest(BaseModel):
    source_dir: str = Field(..., description="Path to directory with PDFs/HTMLs")
    doc_metadata: dict = Field(
        default_factory=dict,
        description="Metadata about documents (year, version, etc.)"
    )
```

### Response Models

```python
class Citation(BaseModel):
    """Single inline citation in the answer."""
    act: str
    """Act name: "Companies Act 2013" """
    
    section_type: str
    """"Section" | "Rule" | "Regulation" """
    
    section_number: str
    """"42" | "42(3)" | "14(2)(a)" """
    
    section_title: Optional[str] = None
    """Full section title if available."""
    
    chunk_id: Optional[str] = None
    """ID of the retrieved chunk."""
    
    text_excerpt: Optional[str] = None
    """First 200 chars of the section text."""

class QueryResponse(BaseModel):
    answer: str
    """Generated answer with inline citations."""
    
    citations: list[Citation]
    """All extracted citations."""
    
    query_type: str
    """Query classification result."""
    
    iterations: int
    """Number of CRAG iterations performed."""
    
    context_chunks_used: int
    """Count of context chunks sent to LLM."""
    
    graph_nodes_used: int
    """Count of Neo4j nodes included."""

class IngestResponse(BaseModel):
    chunks_created: int
    """Total LegalChunk objects created."""
    
    nodes_created: int
    """Total Neo4j nodes created."""
    
    edges_created: int
    """Total Neo4j edges created."""
    
    duration_seconds: float
    """End-to-end ingestion duration."""

class HealthResponse(BaseModel):
    qdrant: str
    """Service status: "ok" | "error" | "unreachable" """
    
    neo4j: str
    
    openai: str
    
    anthropic: str
    
    status: str
    """Overall: "ready" | "degraded" | "error" """
```

---

## Error Models

```python
class ErrorResponse(BaseModel):
    error: str
    """Error message."""
    
    code: str
    """Error code: INVALID_QUERY | SERVICE_ERROR | CONTEXT_INSUFFICIENT """
    
    timestamp: datetime
```

---

## Entity Models (for graph extraction)

**File**: `clause/ingestion/extractors/entity_extractor.py`

```python
class Section(BaseModel):
    number: str
    title: str
    act: str

class ComplianceObligation(BaseModel):
    name: str
    description: str
    frequency: str  # "annual", "quarterly", "one-time", "event-triggered"
    due_date_logic: str

class Penalty(BaseModel):
    amount_min: float
    amount_max: float
    type: str  # "fine", "imprisonment", "both"
    currency: str  # "INR"

class Definition(BaseModel):
    term: str
    definition_text: str
    defined_in: str  # section reference

class EntityType(BaseModel):
    name: str  # "PrivateLimited", "PublicLimited", "OPC", "LLP", "SmallCompany"
```

---

## Configuration Model

**File**: `clause/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """All configuration from environment variables."""
    
    # APIs
    anthropic_api_key: str
    openai_api_key: str
    cohere_api_key: str
    langsmith_api_key: Optional[str] = None
    
    # Databases
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "clause_chunks"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str
    
    # Models (locked)
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072
    generation_model: str = "claude-sonnet-4-20250514"
    contextualization_model: str = "claude-haiku-20240307"
    
    # Tuning
    top_k_retrieval: int = 20
    top_k_rerank: int = 5
    max_agent_iterations: int = 3
    
    # Chunking (locked)
    child_chunk_size: int = 256
    parent_chunk_size: int = 1024
    child_chunk_overlap: int = 20
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

---

## Usage Throughout Codebase

**In ingestion:**
```python
chunk: LegalChunk = parse_and_chunk(document)
```

**In retrieval:**
```python
from clause.api.schemas import QueryRequest, QueryResponse
request: QueryRequest = QueryRequest(query="...")
response: QueryResponse = await run_query(request)
```

**In agent:**
```python
from clause.agent.state import ClauseState
state: ClauseState = {...}
```

**In config:**
```python
from clause.config import settings
client = QdrantClient(url=settings.qdrant_url)
```

---

## 🔗 Next Steps

- Graph schema: [11-GRAPH-SCHEMA.md](11-GRAPH-SCHEMA.md)
- Prompts: [12-PROMPTS.md](12-PROMPTS.md)
