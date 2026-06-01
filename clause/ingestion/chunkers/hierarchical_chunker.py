"""
Hierarchical chunker — public entry point for creating parent/child/table chunk trees.

This module wraps section_chunker to provide a clean interface used by pipeline.py.
All chunking logic (splitting, merging, cross-refs, token bounds) lives in section_chunker.py.
"""

import logging
from typing import Optional

from clause.ingestion.chunkers import LegalChunk
from clause.ingestion.chunkers.section_chunker import create_legal_chunks

logger = logging.getLogger(__name__)


def create_hierarchical_chunks(
    parsed_docs: dict[str, str],
    doc_metadata: dict,
    tables_by_file: Optional[dict[str, list[dict]]] = None,
) -> list[LegalChunk]:
    """
    Create hierarchical chunks from all parsed documents.

    Produces three chunk types per document:
    - parent: one complete section (512-1024 tokens) — sent to LLM at generation
    - child:  one sub-section/clause (128-256 tokens) — embedded and retrieved
    - table:  structured table, never split — Rule 4

    Args:
        parsed_docs:    Dict mapping filename → parsed text (from parse_all_documents)
        doc_metadata:   Dict mapping filename → {"act": "Companies Act 2013", ...}
        tables_by_file: Optional dict mapping filename → list of table dicts
                        (from table_extractor.extract_tables). If None, no table
                        chunks are created.

    Returns:
        Flat list of LegalChunk objects across all documents.
    """
    tables_by_file = tables_by_file or {}
    all_chunks: list[LegalChunk] = []

    for filename, text in parsed_docs.items():
        # Infer act name from metadata or filename
        act_name = doc_metadata.get(filename, {}).get("act", filename.split("_")[0])
        chapter = doc_metadata.get(filename, {}).get("chapter")
        file_tables = tables_by_file.get(filename, [])

        logger.info(f"Chunking {filename} (act: {act_name})")

        chunks = create_legal_chunks(
            text=text,
            act=act_name,
            chapter=chapter,
            source_file=filename,
            tables=file_tables if file_tables else None,
        )

        all_chunks.extend(chunks)
        logger.info(f"Created {len(chunks)} chunks from {filename}")

    logger.info(f"Total chunks created: {len(all_chunks)}")
    return all_chunks
