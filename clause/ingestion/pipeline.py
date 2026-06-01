"""Ingestion pipeline orchestration."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from clause.ingestion.parsers.pdf_parser import parse_pdf
from clause.ingestion.parsers.html_parser import parse_html
from clause.ingestion.parsers.table_extractor import extract_tables
from clause.ingestion.chunkers.hierarchical_chunker import create_hierarchical_chunks
from clause.ingestion.chunkers import LegalChunk
from clause.ingestion.enrichment.contextualizer import contextualize_all
from clause.indexing.vector_indexer import index_chunks_to_qdrant
from clause.indexing.bm25_indexer import build_bm25_index
from clause.indexing.graph_indexer import build_knowledge_graph

logger = logging.getLogger(__name__)


def parse_all_documents(source_dir: str) -> tuple[dict[str, str], dict[str, list[dict]]]:
    """
    Parse all PDFs and HTMLs in a directory.
    Also extracts tables from PDFs via camelot (lattice mode).

    Args:
        source_dir: Directory containing raw documents

    Returns:
        Tuple of:
        - parsed_docs:    Dict mapping filename → parsed text
        - tables_by_file: Dict mapping filename → list of table dicts
    """
    source_path = Path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    parsed_docs: dict[str, str] = {}
    tables_by_file: dict[str, list[dict]] = {}

    # Parse PDFs (text + tables)
    for pdf_file in source_path.glob("**/*.pdf"):
        try:
            text = parse_pdf(str(pdf_file))
            parsed_docs[pdf_file.name] = text
        except Exception as e:
            logger.error(f"Failed to parse {pdf_file.name}: {e}")

        try:
            tables = extract_tables(str(pdf_file))
            if tables:
                tables_by_file[pdf_file.name] = tables
        except Exception as e:
            logger.warning(f"Failed to extract tables from {pdf_file.name}: {e}")

    # Parse HTMLs
    for html_file in source_path.glob("**/*.html"):
        try:
            text = parse_html(str(html_file))
            parsed_docs[html_file.name] = text
        except Exception as e:
            logger.error(f"Failed to parse {html_file.name}: {e}")

    logger.info(f"Parsed {len(parsed_docs)} documents from {source_dir}")
    logger.info(f"Extracted tables from {len(tables_by_file)} PDFs")
    return parsed_docs, tables_by_file


async def run_ingestion_pipeline(
    source_dir: str = "data/raw/",
    output_dir: str = "data/processed/",
    skip_enrichment: bool = False,
    skip_indexing: bool = False,
) -> dict:
    """
    Full pipeline: Parse → Chunk → Enrich → Index

    This is the main entry point called by:
    - CLI (scripts/run_ingestion.py)
    - API (POST /ingest)

    Args:
        source_dir: Directory with raw PDFs/HTMLs
        output_dir: Directory to save processed chunks
        skip_enrichment: If True, skip Claude enrichment (for testing)

    Returns:
        Dict with pipeline stats (chunks_created, nodes_created, etc.)
    """
    logger.info("=" * 60)
    logger.info("Starting ingestion pipeline")
    logger.info("=" * 60)

    # Show enrichment config upfront so user can verify before slow parsing begins
    from clause.config import settings
    if skip_enrichment:
        logger.info("Enrichment: SKIPPED (--skip-enrichment flag)")
    elif settings.enrichment_provider == "ollama":
        logger.info(f"Enrichment: Ollama  model={settings.ollama_model}  url={settings.ollama_base_url}")
    else:
        logger.info(f"Enrichment: Claude  model={settings.contextualization_model}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 1: Parse all PDFs and HTMLs (also extracts tables)
    logger.info("\n[Step 1] Parsing documents...")
    parsed_docs, tables_by_file = parse_all_documents(source_dir)

    if not parsed_docs:
        logger.warning("No documents found to parse")
        return {"chunks_created": 0, "documents_parsed": 0}

    # Step 2: Create chunks with hierarchy (parent, child, table)
    logger.info("\n[Step 2] Creating hierarchical chunks...")
    doc_metadata: dict = {}  # Can be extended with act metadata
    chunks = create_hierarchical_chunks(parsed_docs, doc_metadata, tables_by_file)

    # Save raw chunks
    chunks_file = output_path / "chunks" / "raw_chunks.json"
    chunks_file.parent.mkdir(parents=True, exist_ok=True)
    chunks_json = [chunk.dict() for chunk in chunks]
    with open(chunks_file, "w") as f:
        json.dump(chunks_json, f, indent=2, default=str)
    logger.info(f"Saved {len(chunks)} raw chunks to {chunks_file}")

    # Step 3: Enrich chunks with context (optional)
    if not skip_enrichment:
        logger.info("\n[Step 3] Enriching chunks with context...")
        # Only child chunks need contextualisation; table chunks are used as-is
        children = [c for c in chunks if c.type == "child"]
        parents = {c.chunk_id: c for c in chunks if c.type == "parent"}

        enriched_children = await contextualize_all(children, parents)

        # Replace children in chunks list
        chunks = [c for c in chunks if c.type != "child"]
        chunks.extend(enriched_children)

        # Save enriched chunks
        enriched_file = output_path / "chunks" / "enriched_chunks.json"
        enriched_file.parent.mkdir(parents=True, exist_ok=True)
        enriched_json = [chunk.dict() for chunk in chunks]
        with open(enriched_file, "w") as f:
            json.dump(enriched_json, f, indent=2, default=str)
        logger.info(f"Saved {len(chunks)} enriched chunks to {enriched_file}")
    else:
        logger.info("[Step 3] Skipping enrichment (test mode)")

    # Convert LegalChunk objects to plain dicts for indexers
    chunks_json = [chunk.dict() for chunk in chunks]

    nodes_created = 0
    edges_created = 0
    points_indexed = 0

    if skip_indexing:
        logger.info("\n[Steps 4-6] Indexing SKIPPED (--skip-indexing flag)")
    else:
        # Step 4: Embedding & Vector Indexing (Qdrant)
        logger.info("\n[Step 4] Embedding & indexing into Qdrant...")
        points_indexed = index_chunks_to_qdrant(chunks_json)

        # Step 5: BM25 Sparse Indexing
        logger.info("\n[Step 5] Building BM25 sparse index...")
        bm25_path = str(output_path / "bm25_index.pkl")
        build_bm25_index(chunks_json, index_path=bm25_path)

        # Step 6: Knowledge Graph Construction (Neo4j)
        logger.info("\n[Step 6] Building knowledge graph in Neo4j...")
        nodes_created, edges_created = build_knowledge_graph(
            chunks_json, clear_existing=True
        )

    # Count chunk types
    chunk_counts: dict[str, int] = {}
    for chunk in chunks:
        chunk_counts[chunk.type] = chunk_counts.get(chunk.type, 0) + 1

    logger.info("\n" + "=" * 60)
    logger.info("Ingestion pipeline complete!")
    logger.info("=" * 60)
    logger.info(f"Documents parsed: {len(parsed_docs)}")
    logger.info("Chunks created by type:")
    for chunk_type, count in chunk_counts.items():
        logger.info(f"  - {chunk_type}: {count}")
    logger.info(f"Total chunks: {len(chunks)}")
    if not skip_indexing:
        logger.info(f"Qdrant points: {points_indexed}")
        logger.info(f"Neo4j nodes: {nodes_created} | edges: {edges_created}")

    return {
        "documents_parsed": len(parsed_docs),
        "chunks_created": len(chunks),
        "chunk_counts": chunk_counts,
        "points_indexed": points_indexed,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
    }


if __name__ == "__main__":
    # Test run
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run with optional flags for testing
    skip_enrichment = "--skip-enrichment" in sys.argv
    skip_indexing = "--skip-indexing" in sys.argv
    result = asyncio.run(
        run_ingestion_pipeline(
            skip_enrichment=skip_enrichment,
            skip_indexing=skip_indexing,
        )
    )
    print(json.dumps(result, indent=2))
