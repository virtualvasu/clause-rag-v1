"""
Hybrid retriever — fuses vector, BM25, and graph signals using
Reciprocal Rank Fusion (RRF), then reranks top candidates.

Pipeline:
    query
      ├── vector_search()     → top-K by semantic similarity (Qdrant)
      ├── bm25_search()       → top-K by keyword match (BM25)
      └── expand_with_graph() → sibling/adjacent/xref chunks (Neo4j)
          ↓
      RRF fusion → unified ranked list (top 20)
          ↓
      rerank()  → cross-encoder → top 5
"""

import logging
import pickle
from pathlib import Path

from clause.config import settings
from clause.retrieval.vector_retriever import vector_search
from clause.indexing.bm25_indexer import bm25_search, load_bm25_index
from clause.retrieval.graph_retriever import expand_with_graph, get_parent_context

logger = logging.getLogger(__name__)

# BM25 index cache — loaded once per process
_bm25_cache: tuple | None = None
BM25_INDEX_PATH = "data/processed/bm25_index.pkl"


def _get_bm25():
    global _bm25_cache
    if _bm25_cache is None:
        _bm25_cache = load_bm25_index(BM25_INDEX_PATH)
    return _bm25_cache


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def _rrf_fuse(
    ranked_lists: list[list[dict]],
    id_key: str = "chunk_id",
    k: int = 60,
) -> list[dict]:
    """
    Fuse multiple ranked lists using Reciprocal Rank Fusion.

    RRF score = Σ  1 / (k + rank_i)

    Higher k → less weight on top ranks (more conservative fusion).
    k=60 is the standard default from the original RRF paper.
    """
    scores: dict[str, float] = {}
    chunk_store: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, chunk in enumerate(ranked_list, start=1):
            cid = chunk[id_key]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            chunk_store[cid] = chunk  # keep latest copy of chunk data

    fused = sorted(chunk_store.values(), key=lambda c: scores[c[id_key]], reverse=True)

    # Attach RRF score for inspection
    for chunk in fused:
        chunk["rrf_score"] = round(scores[chunk[id_key]], 6)

    return fused


# ── Reranker ──────────────────────────────────────────────────────────────────

def rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """
    Rerank candidates using a local cross-encoder.
    Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (free, ~80 MB, no API key)

    The cross-encoder reads (query, chunk_text) pairs together and produces
    a precise relevance score — much more accurate than vector similarity alone.
    """
    from sentence_transformers import CrossEncoder

    if not candidates:
        return []

    logger.info(f"Reranking {len(candidates)} candidates with cross-encoder")
    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    # Use contextualized_text if available, else raw text
    pairs = [
        [query, c.get("contextualized_text") or c.get("text", "")]
        for c in candidates
    ]
    scores = model.predict(pairs)

    for chunk, score in zip(candidates, scores):
        chunk["rerank_score"] = float(score)

    reranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    return reranked[:top_k]


# ── Main hybrid retrieval function ────────────────────────────────────────────

def hybrid_retrieve(
    query: str,
    top_k_retrieval: int | None = None,
    top_k_rerank: int | None = None,
    filter_act: str | None = None,
    use_graph: bool = True,
    use_reranker: bool = True,
) -> dict:
    """
    Full hybrid retrieval pipeline.

    Args:
        query:           Natural language legal question
        top_k_retrieval: Candidates to gather before reranking (default: settings.top_k_retrieval)
        top_k_rerank:    Final results after reranking (default: settings.top_k_rerank)
        filter_act:      Restrict to a specific act (e.g. "SEBI", "Companies")
        use_graph:       Whether to include graph expansion (default: True)
        use_reranker:    Whether to apply cross-encoder reranking (default: True)

    Returns:
        Dict with:
          - 'results':      Final ranked list of chunks (top_k_rerank)
          - 'candidates':   All fused candidates before reranking
          - 'vector_hits':  Raw vector search results
          - 'bm25_hits':    Raw BM25 results
          - 'graph_hits':   Graph expansion results
    """
    top_k_retrieval = top_k_retrieval or settings.top_k_retrieval
    top_k_rerank    = top_k_rerank    or settings.top_k_rerank

    logger.info(f"Hybrid retrieve | query='{query[:80]}' | act_filter={filter_act}")

    # ── 1. Vector search ──────────────────────────────────────────────────
    vector_hits = vector_search(query, top_k=top_k_retrieval, filter_act=filter_act)

    # ── 2. BM25 search ────────────────────────────────────────────────────
    bm25, bm25_chunks = _get_bm25()
    bm25_hits = bm25_search(query, bm25, bm25_chunks, top_k=top_k_retrieval)

    # Filter BM25 by act if requested
    if filter_act:
        bm25_hits = [c for c in bm25_hits if c.get("act") == filter_act]

    # ── 3. RRF fusion ─────────────────────────────────────────────────────
    fused = _rrf_fuse([vector_hits, bm25_hits])

    # ── 4. Graph expansion ────────────────────────────────────────────────
    graph_hits: list[dict] = []
    if use_graph:
        seed_ids = [c["chunk_id"] for c in fused[:10]]  # expand top-10 seeds
        graph_hits = expand_with_graph(seed_ids, hops=1)

        # Add graph hits to fused list (they get lower implicit rank via RRF)
        if graph_hits:
            fused = _rrf_fuse([fused, graph_hits])

    # Take top candidates for reranking
    candidates = fused[:top_k_retrieval]

    # ── 5. Rerank ─────────────────────────────────────────────────────────
    if use_reranker and candidates:
        results = rerank(query, candidates, top_k=top_k_rerank)
    else:
        results = candidates[:top_k_rerank]

    logger.info(
        f"Retrieval complete | vector={len(vector_hits)} bm25={len(bm25_hits)} "
        f"graph={len(graph_hits)} → fused={len(candidates)} → final={len(results)}"
    )

    return {
        "results":     results,
        "candidates":  candidates,
        "vector_hits": vector_hits,
        "bm25_hits":   bm25_hits,
        "graph_hits":  graph_hits,
    }
