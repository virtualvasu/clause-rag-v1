"""
Query and health routes.
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from clause.api.schemas import (
    QueryRequest,
    QueryResponse,
    HealthResponse,
    GraphStatsResponse,
    RetrievalStats,
    Citation,
)
from clause.query import answer_query
from clause.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ── POST /query ────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Answer a legal question using the full hybrid RAG pipeline.

    - Retrieves relevant chunks from Qdrant (vector) + BM25 + Neo4j (graph)
    - Optionally runs CRAG quality check and refines the query
    - Generates an answer using Ollama (local) with inline citations
    """
    logger.info(f"POST /query | query='{request.query[:80]}'")

    try:
        result = answer_query(
            query=request.query,
            filter_act=request.filter_act,
            use_graph=request.use_graph,
            use_crag=request.use_crag,
        )
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return QueryResponse(
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
        query=result["query"],
        final_query=result["final_query"],
        iterations=result["iterations"],
        crag_score=result["crag_score"],
        chunks_used=result["chunks_used"],
        provider=result["provider"],
        retrieval=RetrievalStats(**result["retrieval"]),
    )


# ── GET /health ────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check connectivity to all backend services."""
    results = {}

    # Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=settings.qdrant_url, timeout=3)
        client.get_collections()
        results["qdrant"] = "ok"
    except Exception as e:
        results["qdrant"] = f"error: {e}"

    # Neo4j
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
        with driver.session() as s:
            s.run("RETURN 1")
        driver.close()
        results["neo4j"] = "ok"
    except Exception as e:
        results["neo4j"] = f"error: {e}"

    # Ollama
    try:
        import httpx
        r = httpx.get(settings.ollama_base_url.replace("/v1", ""), timeout=3)
        results["ollama"] = "ok" if r.status_code == 200 else f"http {r.status_code}"
    except Exception as e:
        results["ollama"] = f"error: {e}"

    all_ok = all(v == "ok" for v in results.values())
    results["status"] = "ready" if all_ok else "degraded"

    return HealthResponse(**results)


# ── GET /graph/stats ───────────────────────────────────────────────────────────

@router.get("/graph/stats", response_model=GraphStatsResponse)
async def graph_stats():
    """Return knowledge graph statistics."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
        with driver.session() as session:
            node_result  = session.run("MATCH (n) RETURN count(n) AS count").single()
            edge_result  = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()
            acts_result  = session.run("MATCH (a:Act) RETURN a.name AS name").data()
            sect_result  = session.run("MATCH (s:Section) RETURN count(s) AS count").single()
            chunk_result = session.run("MATCH (c:Chunk) RETURN count(c) AS count").single()
        driver.close()

        return GraphStatsResponse(
            nodes=node_result["count"],
            edges=edge_result["count"],
            acts=[r["name"] for r in acts_result],
            sections=sect_result["count"],
            chunks=chunk_result["count"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
