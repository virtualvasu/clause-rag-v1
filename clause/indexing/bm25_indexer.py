"""BM25 sparse indexing for keyword/exact-match retrieval."""

import json
import logging
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# Default path for the persisted BM25 index
DEFAULT_INDEX_PATH = "data/processed/bm25_index.pkl"


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer. Legal text benefits from keeping numbers."""
    return text.lower().split()


def build_bm25_index(
    chunks: list[dict],
    index_path: str = DEFAULT_INDEX_PATH,
) -> tuple["BM25Okapi", list[dict]]:
    """
    Build a BM25Okapi index from child + table chunks and persist it to disk.

    Indexes:
    - child chunks  → contextualized_text (if available), else text
    - table chunks  → text (raw markdown table)

    Returns:
        (bm25_index, indexed_chunks) — indexed_chunks preserves chunk order
        so bm25.get_scores(query) maps 1:1 to indexed_chunks.
    """
    indexable = [c for c in chunks if c["type"] in ("child", "table")]
    logger.info(f"Building BM25 index over {len(indexable)} chunks")

    corpus: list[list[str]] = []
    for chunk in indexable:
        if chunk["type"] == "child" and chunk.get("contextualized_text"):
            text = chunk["contextualized_text"]
        else:
            text = chunk["text"]
        corpus.append(_tokenize(text))

    bm25 = BM25Okapi(corpus)

    # Persist both the index and the chunk metadata (needed for retrieval)
    index_path_obj = Path(index_path)
    index_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path_obj, "wb") as f:
        pickle.dump(
            {
                "bm25": bm25,
                "chunks": indexable,  # parallel list to corpus
            },
            f,
        )

    logger.info(f"✓ BM25 index saved to {index_path_obj}")
    return bm25, indexable


def load_bm25_index(
    index_path: str = DEFAULT_INDEX_PATH,
) -> tuple["BM25Okapi", list[dict]]:
    """Load a previously persisted BM25 index from disk."""
    with open(index_path, "rb") as f:
        data = pickle.load(f)
    logger.info(f"Loaded BM25 index ({len(data['chunks'])} chunks) from {index_path}")
    return data["bm25"], data["chunks"]


def bm25_search(
    query: str,
    bm25: "BM25Okapi",
    indexed_chunks: list[dict],
    top_k: int = 20,
) -> list[dict]:
    """
    Run a BM25 keyword search.

    Returns top_k chunks sorted by BM25 score (descending), each with
    an added 'bm25_score' key.
    """
    tokens = _tokenize(query)
    scores = bm25.get_scores(tokens)

    # Pair chunks with scores and sort
    scored = sorted(
        zip(scores, indexed_chunks),
        key=lambda x: x[0],
        reverse=True,
    )

    results = []
    for score, chunk in scored[:top_k]:
        result = dict(chunk)
        result["bm25_score"] = float(score)
        results.append(result)

    return results
