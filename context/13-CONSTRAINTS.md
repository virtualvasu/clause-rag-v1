# 13 — Non-Negotiable Constraints

**Read this section before every coding session.**

---

## 🔴 Core Architecture

### Vector Database
✅ **Use:** Qdrant only

### Orchestration
✅ **Use:** LangGraph only

### Hybrid Retrieval
✅ **Use:** BM25 + Dense + RRF fusion

### Reranker
✅ **Use:** Cohere Rerank v3

### Graph Database
✅ **Use:** Neo4j 5.x only

### Generation LLM
✅ **Use:** Claude Sonnet 4 (`claude-sonnet-4-20250514`) only

### Embedding Model
✅ **Use:** text-embedding-3-large (3072 dimensions) only

### Contextualization LLM
✅ **Use:** Claude Haiku only

---

## 🔴 Data Pipeline

### Chunking Strategy
✅ **Use:** Hierarchical legal-aware chunking only

**Rules:**
1. Never split provisos from their parent clause (`"Provided that..."`)
2. Never split explanations from their section (`"Explanation — For..."`
3. Child chunks: 128–256 tokens
4. Parent chunks: 512–1024 tokens
5. Cross-references must be extracted and stored

### Chunk Hierarchy
✅ **Use:** Three-level hierarchy (document, parent, child)

### Contextual Enrichment
✅ **Use:** LLM-generated 1-2 sentence context from parent section only

---

## 🔴 Retrieval Pipeline

### Query Classification
✅ **Use:** Four query types (SIMPLE, MULTI_HOP, CROSS_DOC, CONDITIONAL)

**Why:** Determines which downstream components to activate (graph, CRAG, etc.)

### Query Expansion
✅ **Use:** Original + 3 alternative phrasings

### HyDE
✅ **Always generate:** Hypothetical document passage

### Sparse Retrieval
✅ **Use:** BM25s for all queries

### RRF Fusion
✅ **Use:** Reciprocal Rank Fusion (k=60)

### Reranking
✅ **Always rerank:** Top-20 RRF results to top-5 with Cohere

### Parent Fetch
✅ **Always fetch:** Parent section for context

---

## 🔴 Agent Loop

### CRAG Pattern
✅ **Use:** CRAG (Corrective RAG) with context quality check

### Iteration Limit
✅ **Use:** Maximum 3 iterations

### Context Score Threshold
✅ **Use:** 0.6 (re-retrieve if score < 0.6)

### Graph Traversal
✅ **Always enable:** Neo4j traversal for MULTI_HOP/CROSS_DOC/CONDITIONAL

---

## 🔴 Evaluation

### RAGAS Metrics
✅ **Use:** All four RAGAS metrics on 20-question benchmark

### Ablation Benchmark
✅ **Run:** Three variants (NAIVE, ADVANCED, FULL)

### Test Categories
✅ **Use:** 5 SIMPLE + 5 MULTI_HOP + 5 CROSS_DOC + 5 CONDITIONAL

---

## 🔴 Code Quality

### Type Hints
✅ **Always add:** Full type hints with return types

### Docstrings
✅ **Always add:** Function-level docstring

### Prompt Definition
✅ **Always centralize:** All prompts in `clause/generation/prompts.py`

### Config Management
✅ **Always use:** Settings from `clause/config.py`

### Testing
✅ **Always write:** Unit tests for critical paths

---

## Summary Table

| Component | Locked Choice |
|-----------|---------------|
| **Vector DB** | Qdrant |
| **Orchestration** | LangGraph |
| **Retrieval** | Hybrid (Dense + Sparse + RRF) |
| **Reranker** | Cohere Rerank v3 |
| **Graph DB** | Neo4j |
| **Gen LLM** | Claude Sonnet 4 |
| **Embedding** | text-embedding-3-large |
| **Context LLM** | Claude Haiku |
| **Chunking** | Hierarchical legal-aware |
| **Fusion** | RRF |
| **Evaluation** | RAGAS on 20-question ablation |

