"""Vector indexing into Qdrant.

Embedding providers:
- "local"  → BAAI/bge-large-en-v1.5 via sentence-transformers (free, 1024 dims)
- "openai" → text-embedding-3-large via OpenAI API (paid, 3072 dims)
"""

import logging
import time
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
)

from clause.config import settings

logger = logging.getLogger(__name__)

# Qdrant payload field names
FIELD_CHUNK_ID = "chunk_id"
FIELD_TYPE = "type"
FIELD_ACT = "act"
FIELD_SECTION = "section_number"
FIELD_SECTION_TITLE = "section_title"
FIELD_PARENT_ID = "parent_id"
FIELD_SOURCE_FILE = "source_file"
FIELD_TEXT = "text"
FIELD_CTX_TEXT = "contextualized_text"
FIELD_TOKENS = "tokens"


# ── Qdrant client ──────────────────────────────────────────────────────────────

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection(client: QdrantClient, recreate: bool = False) -> None:
    """Create Qdrant collection if it doesn't exist. Optionally recreate."""
    name = settings.qdrant_collection_name

    if client.collection_exists(name):
        if recreate:
            logger.warning(f"Recreating collection '{name}'")
            client.delete_collection(name)
        else:
            logger.info(f"Collection '{name}' already exists — skipping creation")
            return

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=settings.embedding_dimensions,
            distance=Distance.COSINE,
        ),
    )

    # Payload indexes for fast metadata filtering
    client.create_payload_index(name, FIELD_ACT, PayloadSchemaType.KEYWORD)
    client.create_payload_index(name, FIELD_TYPE, PayloadSchemaType.KEYWORD)
    client.create_payload_index(name, FIELD_SECTION, PayloadSchemaType.KEYWORD)

    logger.info(
        f"Created Qdrant collection '{name}' "
        f"(dim={settings.embedding_dimensions}, metric=cosine)"
    )


# ── Embedding backends ─────────────────────────────────────────────────────────

def _embed_local(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Embed using BAAI/bge-large-en-v1.5 via sentence-transformers.
    Downloads model on first call (~1.3 GB), cached in ~/.cache/huggingface/.
    BGE models work best with the instruction prefix for retrieval tasks.
    """
    from sentence_transformers import SentenceTransformer

    logger.info(f"Loading local embedding model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)

    all_embeddings: list[list[float]] = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.info(
            f"Embedding batch {i // batch_size + 1}/{total_batches} "
            f"({len(batch)} texts)"
        )
        # BGE instruction prefix improves retrieval quality
        prefixed = [f"Represent this sentence for searching relevant passages: {t}" for t in batch]
        vecs = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
        all_embeddings.extend(vecs.tolist())

    return all_embeddings


def _embed_openai(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Embed using OpenAI text-embedding-3-large (requires OPENAI_API_KEY)."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    all_embeddings: list[list[float]] = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.info(
            f"Embedding batch {i // batch_size + 1}/{total_batches} "
            f"({len(batch)} texts)"
        )
        response = client.embeddings.create(input=batch, model=settings.embedding_model)
        all_embeddings.extend([e.embedding for e in response.data])
        if i + batch_size < len(texts):
            time.sleep(0.5)  # rate-limit buffer

    return all_embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Route embedding to the configured provider."""
    provider = settings.embedding_provider
    logger.info(f"Embedding provider: {provider} | model: {settings.embedding_model}")

    if provider == "local":
        return _embed_local(texts)
    elif provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in .env")
        return _embed_openai(texts)
    else:
        raise ValueError(f"Unknown embedding_provider '{provider}'. Use 'local' or 'openai'.")


# ── Main indexing function ─────────────────────────────────────────────────────

def index_chunks_to_qdrant(
    chunks: list[dict],
    recreate: bool = False,
    upsert_batch_size: int = 200,
) -> int:
    """
    Embed and upsert chunks into Qdrant.

    What gets indexed:
    - child chunks  → contextualized_text (enriched context + raw text)
    - table chunks  → text (raw markdown table)
    - parent chunks → skipped (used for context expansion during retrieval, not search)

    Returns number of points upserted.
    """
    qdrant = get_qdrant_client()
    ensure_collection(qdrant, recreate=recreate)

    indexable = [c for c in chunks if c["type"] in ("child", "table")]
    logger.info(f"Indexing {len(indexable)} chunks (child + table) into Qdrant")

    # Pick the right text to embed per chunk
    embed_inputs: list[str] = []
    for chunk in indexable:
        if chunk["type"] == "child" and chunk.get("contextualized_text"):
            embed_inputs.append(chunk["contextualized_text"])
        else:
            embed_inputs.append(chunk["text"])

    embeddings = embed_texts(embed_inputs)

    # Build Qdrant PointStructs
    points: list[PointStruct] = []
    for i, (chunk, vector) in enumerate(zip(indexable, embeddings)):
        payload = {
            FIELD_CHUNK_ID:      chunk["chunk_id"],
            FIELD_TYPE:          chunk["type"],
            FIELD_ACT:           chunk.get("act", ""),
            FIELD_SECTION:       chunk.get("section_number", ""),
            FIELD_SECTION_TITLE: chunk.get("section_title", ""),
            FIELD_PARENT_ID:     chunk.get("parent_id"),
            FIELD_SOURCE_FILE:   chunk.get("source_file", ""),
            FIELD_TEXT:          chunk["text"],
            FIELD_CTX_TEXT:      chunk.get("contextualized_text"),
            FIELD_TOKENS:        chunk.get("tokens", 0),
        }
        points.append(PointStruct(id=i, vector=vector, payload=payload))

    # Upsert in batches
    total_upserted = 0
    for i in range(0, len(points), upsert_batch_size):
        batch = points[i : i + upsert_batch_size]
        qdrant.upsert(collection_name=settings.qdrant_collection_name, points=batch)
        total_upserted += len(batch)
        logger.info(f"Upserted {total_upserted}/{len(points)} points into Qdrant")

    logger.info(f"✓ Qdrant indexing complete — {total_upserted} points")
    return total_upserted
