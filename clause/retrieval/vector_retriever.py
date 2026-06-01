"""Vector retrieval from Qdrant using BGE embeddings."""

import logging
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from clause.config import settings

logger = logging.getLogger(__name__)

# Module-level model cache — loaded once, reused across calls
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_query(query: str) -> list[float]:
    """
    Embed a search query using the BGE retrieval instruction prefix.
    Must match the prefix used during indexing for consistent similarity scores.
    """
    model = _get_model()
    prefixed = f"Represent this sentence for searching relevant passages: {query}"
    vector = model.encode(prefixed, normalize_embeddings=True)
    return vector.tolist()


def vector_search(
    query: str,
    top_k: int = 20,
    filter_act: str | None = None,
) -> list[dict]:
    """
    Search Qdrant for semantically similar chunks.

    Args:
        query: Natural language query
        top_k: Number of results to return
        filter_act: Optional — restrict to a specific act (e.g. "Companies", "SEBI")

    Returns:
        List of dicts with chunk payload + 'vector_score' key
    """
    client = QdrantClient(url=settings.qdrant_url)
    query_vector = embed_query(query)

    # Optional metadata filter
    qdrant_filter = None
    if filter_act:
        qdrant_filter = Filter(
            must=[FieldCondition(key="act", match=MatchValue(value=filter_act))]
        )

    results = client.search(
        collection_name=settings.qdrant_collection_name,
        query_vector=query_vector,
        limit=top_k,
        query_filter=qdrant_filter,
        with_payload=True,
    )

    hits = []
    for r in results:
        chunk = dict(r.payload)
        chunk["vector_score"] = r.score
        hits.append(chunk)

    logger.info(f"Vector search: {len(hits)} results for query='{query[:60]}...'")
    return hits
