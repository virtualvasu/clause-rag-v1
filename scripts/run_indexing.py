"""
Run Steps 4-6: Embed → Qdrant, BM25, Neo4j graph.

Usage:
    python scripts/run_indexing.py                   # index enriched chunks (default)
    python scripts/run_indexing.py --raw             # index raw chunks (no enrichment)
    python scripts/run_indexing.py --skip-qdrant     # skip vector indexing
    python scripts/run_indexing.py --skip-bm25       # skip BM25 indexing
    python scripts/run_indexing.py --skip-neo4j      # skip graph indexing
    python scripts/run_indexing.py --recreate        # wipe & recreate Qdrant collection
"""

import json
import logging
import sys
import time
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from clause.indexing.vector_indexer import index_chunks_to_qdrant
from clause.indexing.bm25_indexer import build_bm25_index
from clause.indexing.graph_indexer import build_knowledge_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    args = sys.argv[1:]
    use_raw     = "--raw"         in args
    skip_qdrant = "--skip-qdrant" in args
    skip_bm25   = "--skip-bm25"   in args
    skip_neo4j  = "--skip-neo4j"  in args
    recreate    = "--recreate"    in args

    # ── Load chunks ────────────────────────────────────────────────────────
    if use_raw:
        chunks_file = "data/processed/chunks/raw_chunks.json"
    else:
        chunks_file = "data/processed/chunks/enriched_chunks.json"

    logger.info(f"Loading chunks from: {chunks_file}")
    with open(chunks_file) as f:
        chunks = json.load(f)

    child_count  = sum(1 for c in chunks if c["type"] == "child")
    parent_count = sum(1 for c in chunks if c["type"] == "parent")
    table_count  = sum(1 for c in chunks if c["type"] == "table")
    logger.info(
        f"Loaded {len(chunks)} chunks "
        f"(parent={parent_count}, child={child_count}, table={table_count})"
    )

    results = {}

    # ── Step 4: Qdrant vector indexing ────────────────────────────────────
    if not skip_qdrant:
        logger.info("\n" + "=" * 50)
        logger.info("Step 4: Embedding & Qdrant vector indexing")
        logger.info("=" * 50)
        t0 = time.time()
        points = index_chunks_to_qdrant(chunks, recreate=recreate)
        results["qdrant_points"] = points
        logger.info(f"Step 4 done in {time.time() - t0:.1f}s — {points} points indexed")
    else:
        logger.info("Step 4: SKIPPED (--skip-qdrant)")

    # ── Step 5: BM25 sparse indexing ──────────────────────────────────────
    if not skip_bm25:
        logger.info("\n" + "=" * 50)
        logger.info("Step 5: BM25 sparse indexing")
        logger.info("=" * 50)
        t0 = time.time()
        bm25_path = "data/processed/bm25_index.pkl"
        _, indexed = build_bm25_index(chunks, index_path=bm25_path)
        results["bm25_chunks"] = len(indexed)
        logger.info(f"Step 5 done in {time.time() - t0:.1f}s — {len(indexed)} chunks indexed")
    else:
        logger.info("Step 5: SKIPPED (--skip-bm25)")

    # ── Step 6: Neo4j knowledge graph ─────────────────────────────────────
    if not skip_neo4j:
        logger.info("\n" + "=" * 50)
        logger.info("Step 6: Neo4j knowledge graph construction")
        logger.info("=" * 50)
        t0 = time.time()
        nodes, edges = build_knowledge_graph(chunks, clear_existing=True)
        results["neo4j_nodes"] = nodes
        results["neo4j_edges"] = edges
        logger.info(f"Step 6 done in {time.time() - t0:.1f}s — {nodes} nodes, {edges} edges")
    else:
        logger.info("Step 6: SKIPPED (--skip-neo4j)")

    # ── Summary ────────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 50)
    logger.info("INDEXING COMPLETE")
    logger.info("=" * 50)
    for k, v in results.items():
        logger.info(f"  {k}: {v}")


if __name__ == "__main__":
    main()
