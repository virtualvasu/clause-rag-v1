"""
Pydantic request/response schemas for the Clause API.
All schemas follow the spec in 09-API-FRONTEND.md.
"""

from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    query: str = Field(..., description="Legal question in plain English")
    filter_act: Optional[str] = Field(
        default=None,
        description="Optional: restrict to one act. E.g. 'Companies', 'SEBI', 'DPIIT'",
    )
    use_crag: bool = Field(default=True, description="Enable CRAG quality check + retry loop")
    use_graph: bool = Field(default=True, description="Include Neo4j graph expansion")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the duties of a director under Companies Act?",
                "filter_act": None,
                "use_crag": True,
                "use_graph": True,
            }
        }


class Citation(BaseModel):
    act: str
    section_type: str               # "Section" | "Rule" | "Regulation"
    section_number: str
    section_title: Optional[str] = None
    chunk_id: Optional[str] = None
    text_excerpt: Optional[str] = None


class RetrievalStats(BaseModel):
    vector_hits: int
    bm25_hits: int
    graph_hits: int
    candidates: int


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    query: str
    final_query: str                # after CRAG refinement (may differ from original)
    iterations: int
    crag_score: float
    chunks_used: int
    provider: str                   # "ollama" | "claude"
    retrieval: RetrievalStats


class HealthResponse(BaseModel):
    qdrant: str                     # "ok" | "error: <msg>"
    neo4j: str
    ollama: str
    status: str                     # "ready" | "degraded" | "error"


class GraphStatsResponse(BaseModel):
    nodes: int
    edges: int
    acts: list[str]
    sections: int
    chunks: int
