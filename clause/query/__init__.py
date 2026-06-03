"""
Full query pipeline: retrieval → (CRAG check) → generation.

This is the main entry point for answering a legal question.
The agent loop (06-AGENT-LOOP.md) builds on top of this.

Usage:
    from clause.query.pipeline import answer_query
    result = answer_query("What is the penalty for late filing under Companies Act?")
"""

import logging
from clause.retrieval.hybrid_retriever import hybrid_retrieve
from clause.generation.generator import generate_answer, crag_check, refine_query
from clause.config import settings

logger = logging.getLogger(__name__)


def answer_query(
    query: str,
    filter_act: str | None = None,
    use_graph: bool = True,
    use_reranker: bool = True,
    use_crag: bool = True,
    max_iterations: int | None = None,
    top_k_retrieval: int | None = None,
    top_k_rerank: int | None = None,
) -> dict:
    """
    Full pipeline: retrieve → CRAG check → generate.

    Args:
        query:          User's legal question
        filter_act:     Restrict retrieval to one act (e.g. "DPIIT", "Companies")
        use_graph:      Include Neo4j graph expansion
        use_reranker:   Apply cross-encoder reranking
        use_crag:       Enable CRAG quality check + retry loop
        max_iterations: Max CRAG retries (default: settings.max_agent_iterations)
        top_k_retrieval: Candidates before reranking
        top_k_rerank:    Final chunks passed to LLM

    Returns:
        {
            "answer":         str   — final answer with inline citations
            "citations":      list  — structured citation objects
            "query":          str   — original query
            "final_query":    str   — query after refinement (if CRAG ran)
            "iterations":     int   — number of retrieval attempts
            "crag_score":     float — final context quality score
            "chunks_used":    int   — chunks passed to LLM
            "provider":       str   — LLM used for generation
            "retrieval":      dict  — raw retrieval stats
        }
    """
    max_iterations = max_iterations or settings.max_agent_iterations
    top_k_retrieval = top_k_retrieval or settings.top_k_retrieval
    top_k_rerank = top_k_rerank or settings.top_k_rerank

    current_query = query
    iteration = 0
    crag_score = 1.0  # default if CRAG disabled
    retrieval_result = {}

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Retrieval iteration {iteration}/{max_iterations} | query='{current_query[:70]}'")

        # ── Retrieve ──────────────────────────────────────────────────────
        retrieval_result = hybrid_retrieve(
            query=current_query,
            top_k_retrieval=top_k_retrieval,
            top_k_rerank=top_k_rerank,
            filter_act=filter_act,
            use_graph=use_graph,
            use_reranker=use_reranker,
        )
        context_chunks = retrieval_result["results"]

        # ── CRAG check ────────────────────────────────────────────────────
        if use_crag:
            crag_result = crag_check(current_query, context_chunks)
            crag_score = crag_result["score"]
            logger.info(
                f"CRAG score={crag_score:.2f} | reason='{crag_result['reason'][:60]}'"
            )

            if crag_score >= 0.6 or iteration >= max_iterations:
                break  # context is sufficient, or we've hit max retries

            # Refine query for next iteration
            logger.info(f"CRAG score too low — refining query (missing: {crag_result['missing_info'][:80]})")
            current_query = refine_query(query, crag_result["missing_info"])
            logger.info(f"Refined query: '{current_query[:80]}'")
        else:
            break  # no CRAG — single retrieval pass

    # ── Generate ──────────────────────────────────────────────────────────
    logger.info(f"Generating answer from {len(context_chunks)} chunks")
    generation_result = generate_answer(
        query=query,  # always use original query for generation
        context_chunks=context_chunks,
    )

    return {
        "answer":      generation_result["answer"],
        "citations":   generation_result["citations"],
        "query":       query,
        "final_query": current_query,
        "iterations":  iteration,
        "crag_score":  crag_score,
        "chunks_used": generation_result["chunks_used"],
        "provider":    generation_result["provider"],
        "context_texts": [c.get("text", "") for c in context_chunks],  # for RAGAS eval
        "retrieval": {
            "vector_hits": len(retrieval_result.get("vector_hits", [])),
            "bm25_hits":   len(retrieval_result.get("bm25_hits", [])),
            "graph_hits":  len(retrieval_result.get("graph_hits", [])),
            "candidates":  len(retrieval_result.get("candidates", [])),
        },
    }
