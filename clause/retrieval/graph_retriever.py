"""Graph-based retrieval and context expansion via Neo4j."""

import logging
from neo4j import GraphDatabase

from clause.config import settings

logger = logging.getLogger(__name__)


def _get_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )


def expand_with_graph(chunk_ids: list[str], hops: int = 1) -> list[dict]:
    """
    Given a list of chunk_ids (from vector/BM25 results), expand context
    using the Neo4j graph by fetching:
      - Sibling chunks in the same Section
      - Neighbouring sections (NEXT_SECTION)
      - Cross-referenced sections (CROSS_REFERENCES)

    Args:
        chunk_ids: Chunk IDs from prior retrieval steps
        hops: How many relationship hops to traverse (default 1)

    Returns:
        List of additional chunk dicts not already in chunk_ids
    """
    if not chunk_ids:
        return []

    driver = _get_driver()
    expanded = []

    try:
        with driver.session() as session:
            # 1. Sibling chunks — other chunks in the same parent section
            sibling_result = session.run(
                """
                UNWIND $chunk_ids AS cid
                MATCH (c:Chunk {chunk_id: cid})<-[:HAS_CHUNK]-(s:Section)-[:HAS_CHUNK]->(sibling:Chunk)
                WHERE sibling.chunk_id <> cid
                  AND NOT sibling.chunk_id IN $chunk_ids
                RETURN DISTINCT
                    sibling.chunk_id AS chunk_id,
                    sibling.act AS act,
                    sibling.section_number AS section_number,
                    sibling.text AS text,
                    sibling.contextualized_text AS contextualized_text,
                    sibling.type AS type,
                    sibling.tokens AS tokens,
                    'sibling' AS expansion_source
                LIMIT 20
                """,
                chunk_ids=chunk_ids,
            )
            for record in sibling_result:
                expanded.append(dict(record))

            # 2. Adjacent sections (prev/next in same act)
            adjacent_result = session.run(
                """
                UNWIND $chunk_ids AS cid
                MATCH (c:Chunk {chunk_id: cid})<-[:HAS_CHUNK]-(s:Section)
                MATCH (s)-[:NEXT_SECTION*1..2]-(adj:Section)-[:HAS_CHUNK]->(adj_chunk:Chunk)
                WHERE NOT adj_chunk.chunk_id IN $chunk_ids
                RETURN DISTINCT
                    adj_chunk.chunk_id AS chunk_id,
                    adj_chunk.act AS act,
                    adj_chunk.section_number AS section_number,
                    adj_chunk.text AS text,
                    adj_chunk.contextualized_text AS contextualized_text,
                    adj_chunk.type AS type,
                    adj_chunk.tokens AS tokens,
                    'adjacent_section' AS expansion_source
                LIMIT 20
                """,
                chunk_ids=chunk_ids,
            )
            for record in adjacent_result:
                expanded.append(dict(record))

            # 3. Cross-referenced sections
            xref_result = session.run(
                """
                UNWIND $chunk_ids AS cid
                MATCH (c:Chunk {chunk_id: cid})-[:CROSS_REFERENCES]->(ref:Section)-[:HAS_CHUNK]->(ref_chunk:Chunk)
                WHERE NOT ref_chunk.chunk_id IN $chunk_ids
                RETURN DISTINCT
                    ref_chunk.chunk_id AS chunk_id,
                    ref_chunk.act AS act,
                    ref_chunk.section_number AS section_number,
                    ref_chunk.text AS text,
                    ref_chunk.contextualized_text AS contextualized_text,
                    ref_chunk.type AS type,
                    ref_chunk.tokens AS tokens,
                    'cross_reference' AS expansion_source
                LIMIT 10
                """,
                chunk_ids=chunk_ids,
            )
            for record in xref_result:
                expanded.append(dict(record))

    finally:
        driver.close()

    # Deduplicate by chunk_id
    seen = set()
    unique = []
    for c in expanded:
        if c["chunk_id"] not in seen:
            seen.add(c["chunk_id"])
            unique.append(c)

    logger.info(f"Graph expansion: {len(unique)} additional chunks from {len(chunk_ids)} seeds")
    return unique


def get_parent_context(chunk_ids: list[str]) -> dict[str, str]:
    """
    Fetch the parent Section text for a list of chunk IDs.
    Used to provide full section context alongside child chunks during generation.

    Returns:
        Dict mapping chunk_id → parent section text
    """
    if not chunk_ids:
        return {}

    driver = _get_driver()
    parent_map = {}

    try:
        with driver.session() as session:
            result = session.run(
                """
                UNWIND $chunk_ids AS cid
                MATCH (c:Chunk {chunk_id: cid})<-[:HAS_CHUNK]-(s:Section)
                RETURN cid AS chunk_id, s.text AS parent_text, s.section_id AS section_id
                """,
                chunk_ids=chunk_ids,
            )
            for record in result:
                parent_map[record["chunk_id"]] = {
                    "parent_text": record["parent_text"],
                    "section_id": record["section_id"],
                }
    finally:
        driver.close()

    return parent_map
