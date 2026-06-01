# 05 — Retrieval Pipeline

Covers Step 7: Query Processing.

---

## Query Classification

**File**: `clause/query/classifier.py`

```python
CLASSIFICATION_PROMPT = """Classify this legal query into exactly one category.

Query: {query}

Categories:
- SIMPLE: Single section lookup. One act, one concept, direct answer.
  Example: "What is the definition of a small company under Companies Act?"

- MULTI_HOP: Requires reasoning across multiple sections of one act.
  Example: "What are all compliance requirements in the first 90 days of incorporation?"

- CROSS_DOC: Requires information from multiple acts or regulations.
  Example: "What SEBI filings are needed when a startup issues CCPS to a foreign VC?"

- CONDITIONAL: Answer depends on conditions (entity type, thresholds, dates).
  Example: "What are the audit requirements for a startup with turnover between 2Cr and 10Cr?"

Return ONLY one word: SIMPLE, MULTI_HOP, CROSS_DOC, or CONDITIONAL
"""

# Routing logic:
# SIMPLE → hybrid retrieval only, no graph
# MULTI_HOP → hybrid + graph traversal (1-hop)
# CROSS_DOC → hybrid + graph traversal (2-hop) + query expansion
# CONDITIONAL → full agentic loop with CRAG
```

---

## Query Expansion

**File**: `clause/query/expander.py`

```python
EXPANSION_PROMPT = """You are expanding a legal query to improve retrieval coverage.

Original query: {query}

Generate exactly 3 alternative phrasings of this query. Each phrasing should:
1. Use different legal terminology that might appear in the actual statute
2. Cover different angles of the same question
3. Be specific enough to retrieve relevant sections

Legal documents use formal language like "shall", "notwithstanding", "pursuant to".
Include both formal statutory language and plain English variants.

Return ONLY a JSON array of 3 strings:
["phrasing 1", "phrasing 2", "phrasing 3"]
"""

# All 4 queries (original + 3 expansions) go through hybrid retrieval
# Results are deduplicated by chunk_id before reranking
```

---

## HyDE — Hypothetical Document Embedding

**File**: `clause/retrieval/hyde.py`

```python
HYDE_PROMPT = """Write a short passage that would appear in an Indian legal document 
(Companies Act, SEBI regulation, or MCA rule) that directly answers this question:

Question: {query}

Write as if you are the actual statute text — use formal legal language, section references,
and the phrase structure of Indian legislation. 2-3 sentences maximum.

This hypothetical passage will be embedded and used to search for real statute sections.
"""

# The hypothetical answer is embedded → used for vector search
# The original query text → used for BM25 search
# Results merged via RRF
```

---

## Dense Retrieval

**File**: `clause/retrieval/dense_retriever.py`

```python
from qdrant_client import QdrantClient
from openai import OpenAI

def dense_search(query: str, qdrant_client: QdrantClient, top_k: int = 20) -> list[dict]:
    """
    Vector search on Qdrant using text-embedding-3-large.
    Returns top-K ranked chunks with similarity scores.
    """
    oai = OpenAI()
    query_embedding = oai.embeddings.create(
        input=query,
        model="text-embedding-3-large"
    ).data[0].embedding
    
    results = qdrant_client.search(
        collection_name="clause_chunks",
        query_vector=query_embedding,
        limit=top_k
    )
    
    return [
        {
            "chunk_id": result.payload["chunk_id"],
            "text": result.payload["text"],
            "score": result.score,
            "source": "dense"
        }
        for result in results
    ]
```

---

## Sparse Retrieval

**File**: `clause/retrieval/sparse_retriever.py`

```python
from clause.indexing.bm25_index import load_bm25_index

def sparse_search(query: str, top_k: int = 20) -> list[dict]:
    """
    BM25 keyword search.
    Returns top-K ranked chunks with BM25 scores.
    """
    retriever, chunk_ids, corpus = load_bm25_index()
    results, scores = retriever.retrieve([query], corpus=corpus, k=top_k)
    
    return [
        {
            "chunk_id": chunk_ids[idx],
            "text": corpus[idx],
            "score": float(score),
            "source": "sparse"
        }
        for idx, score in zip(results[0], scores[0])
    ]
```

---

## RRF Fusion

**File**: `clause/retrieval/hybrid_retriever.py`

```python
def reciprocal_rank_fusion(
    dense_results: list[dict],   # [{chunk_id, score}, ...]
    sparse_results: list[dict],  # [{chunk_id, score}, ...]
    k: int = 60,                 # RRF constant — standard value
    top_n: int = 20
) -> list[dict]:
    """
    Combines dense and sparse ranked lists without score normalization.
    RRF score = 1/(k + rank) summed across lists.
    k=60 is standard — do not change without benchmarking.
    """
    scores = {}
    
    for rank, result in enumerate(dense_results):
        cid = result["chunk_id"]
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
    
    for rank, result in enumerate(sparse_results):
        cid = result["chunk_id"]
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
    
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"chunk_id": cid, "rrf_score": score} for cid, score in ranked[:top_n]]
```

---

## Cohere Reranker

**File**: `clause/retrieval/reranker.py`

```python
import cohere

def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    Rerank top-20 RRF results to top-5 using Cohere cross-encoder.
    
    Why rerank after RRF: RRF improves recall but not precision.
    Cross-encoder reranker reads query + document together, giving
    much better relevance judgement than bi-encoder similarity.
    """
    co = cohere.Client()
    
    documents = [c["text"] for c in chunks]
    
    response = co.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=documents,
        top_n=top_n
    )
    
    reranked = []
    for result in response.results:
        chunk = chunks[result.index].copy()
        chunk["rerank_score"] = result.relevance_score
        reranked.append(chunk)
    
    return reranked
```

---

## Parent Chunk Fetcher

**File**: `clause/retrieval/parent_fetcher.py`

```python
def fetch_parents(
    child_chunks: list[dict],
    all_chunks_map: dict[str, LegalChunk]  # chunk_id → LegalChunk
) -> list[dict]:
    """
    Swap child chunks for their parent sections before sending to LLM.
    
    Why: Child chunks (128-256 tokens) are retrieved for precision.
    Parent sections (512-1024 tokens) contain full legal context needed
    for accurate generation. The LLM needs the full section, not a fragment.
    
    Deduplicates: multiple children from same parent → one parent in output.
    """
    seen_parents = set()
    parents = []
    
    for child in child_chunks:
        parent_id = child.get("parent_id")
        if parent_id and parent_id not in seen_parents:
            parent = all_chunks_map.get(parent_id)
            if parent:
                parents.append({
                    **parent.dict(),
                    "retrieved_via_child": child["chunk_id"],
                    "rerank_score": child.get("rerank_score", 0)
                })
                seen_parents.add(parent_id)
    
    return parents
```

---

## Full Retrieval Pipeline

```python
# clause/retrieval/pipeline.py

async def retrieve(query: str, query_type: str = "auto") -> dict:
    """
    Full retrieval pipeline:
    1. Query expansion (if needed)
    2. HyDE generation + embedding
    3. Dense search
    4. Sparse search
    5. RRF fusion
    6. Reranking
    7. Parent fetch
    """
    # Step 1: Expansion
    expanded = [query]
    if query_type in ["MULTI_HOP", "CROSS_DOC"]:
        expanded.extend(await expand_query(query))
    
    # Step 2: HyDE + Dense search
    dense_all = []
    for q in expanded:
        hyde_text = await generate_hyde(q)
        dense_results = dense_search(hyde_text)
        dense_all.extend(dense_results)
    
    # Step 3: Sparse search
    sparse_all = []
    for q in expanded:
        sparse_results = sparse_search(q)
        sparse_all.extend(sparse_results)
    
    # Step 4: Deduplicate and RRF
    rrf_results = reciprocal_rank_fusion(dense_all, sparse_all, top_n=20)
    
    # Step 5: Rerank
    reranked = rerank(query, rrf_results, top_n=5)
    
    # Step 6: Fetch parents
    parents = fetch_parents(reranked)
    
    return {
        "dense_count": len(set(r["chunk_id"] for r in dense_all)),
        "sparse_count": len(set(r["chunk_id"] for r in sparse_all)),
        "rrf_results": rrf_results,
        "reranked": reranked,
        "parent_chunks": parents,
    }
```

---

## 🔗 Next Steps

- Agent loop: [06-AGENT-LOOP.md](06-AGENT-LOOP.md)
- Generation: [07-GENERATION-CITATIONS.md](07-GENERATION-CITATIONS.md)
