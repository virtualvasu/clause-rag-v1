# Clause — Architecture Documentation

> **This is the implementation bible for Claude Code.**
> Read the appropriate sections before writing any code. Every step has a reason. Every decision is locked.

---

## 📚 Documentation Index

This architecture has been broken down into logical, manageable modules. Read sections in order when implementing features, or jump to specific topics as needed.

### Core Architecture & Setup

1. **[01-PROJECT-OVERVIEW.md](01-PROJECT-OVERVIEW.md)** — Start here
   - Project identity and goals
   - Full system architecture diagram
   - Tech stack (locked)
   - Folder structure

2. **[02-INFRASTRUCTURE.md](02-INFRASTRUCTURE.md)** — Before implementation
   - Docker Compose setup (Qdrant + Neo4j)
   - Environment variables (.env)
   - Configuration management (pydantic-settings)

### Implementation Pipeline

3. **[03-INGESTION-PIPELINE.md](03-INGESTION-PIPELINE.md)** — Data ingestion (Steps 1-3)
   - Step 1: Document Parsing (PDF, HTML, tables)
   - Step 2: Hierarchical Chunking (legal structure)
   - Step 3: Contextual Enrichment (LLM-based context generation)

4. **[04-INDEXING.md](04-INDEXING.md)** — Vector & graph indexing (Steps 4-6)
   - Step 4: Embedding & Vector Indexing (Qdrant)
   - Step 5: BM25 Sparse Indexing (keyword search)
   - Step 6: Knowledge Graph Construction (Neo4j)

5. **[05-RETRIEVAL-PIPELINE.md](05-RETRIEVAL-PIPELINE.md)** — Query processing (Step 7)
   - Query Classification (simple / multi-hop / cross-doc / conditional)
   - Query Expansion (3 variants for better recall)
   - HyDE (Hypothetical Document Embedding)
   - Hybrid Retrieval (dense + sparse + RRF + rerank)

6. **[06-AGENT-LOOP.md](06-AGENT-LOOP.md)** — Agentic orchestration (Step 8)
   - LangGraph state machine
   - CRAG (Corrective RAG) pattern
   - Multi-iteration refinement with relevance checking

7. **[07-GENERATION-CITATIONS.md](07-GENERATION-CITATIONS.md)** — Final output (Step 9)
   - LLM generation with context
   - Inline citation extraction
   - Source section references

8. **[08-EVALUATION.md](08-EVALUATION.md)** — Quality assurance (Step 10)
   - RAGAS metrics (faithfulness, relevancy, precision, recall)
   - Evaluation dataset (20 curated questions)
   - Ablation benchmark (3-variant comparison)

### Services & Deployment

9. **[09-API-FRONTEND.md](09-API-FRONTEND.md)** — User-facing layers (Steps 11-12)
   - FastAPI endpoints (/query, /ingest, /health)
   - Streamlit demo UI
   - Request/response schemas

### Reference & Specification

10. **[10-DATA-MODELS.md](10-DATA-MODELS.md)** — Data structures
    - Pydantic models for API requests/responses
    - LegalChunk data model
    - State machine TypedDict

11. **[11-GRAPH-SCHEMA.md](11-GRAPH-SCHEMA.md)** — Neo4j graph design
    - Node labels and properties
    - Relationship types (14 types)
    - Key Cypher queries

12. **[12-PROMPTS.md](12-PROMPTS.md)** — LLM prompts (reference)
    - All prompt templates as constants
    - Classification, expansion, entity extraction
    - Generation, CRAG evaluation
    - ⚠️ All prompts defined in `clause/generation/prompts.py`

13. **[13-CONSTRAINTS.md](13-CONSTRAINTS.md)** — Non-negotiables
    - Architecture decisions that must not change
    - Forbidden substitutions and shortcuts
    - Code quality standards
    - Scope boundaries

---

## 🎯 Quick Navigation

**Implementing a feature?**
- Parsing PDFs → Read [03-INGESTION-PIPELINE.md](03-INGESTION-PIPELINE.md)
- Chunking logic → Read [03-INGESTION-PIPELINE.md](03-INGESTION-PIPELINE.md#step-2--hierarchical-chunking)
- Dense retrieval → Read [05-RETRIEVAL-PIPELINE.md](05-RETRIEVAL-PIPELINE.md)
- Graph queries → Read [11-GRAPH-SCHEMA.md](11-GRAPH-SCHEMA.md)
- API endpoint → Read [09-API-FRONTEND.md](09-API-FRONTEND.md)

**Need to check architecture?**
- Full system flow → Read [01-PROJECT-OVERVIEW.md](01-PROJECT-OVERVIEW.md#2-system-architecture)
- Tech stack → Read [01-PROJECT-OVERVIEW.md](01-PROJECT-OVERVIEW.md#3-tech-stack--locked)

**Uncertain about constraints?**
- What NOT to do → Read [13-CONSTRAINTS.md](13-CONSTRAINTS.md)

---

## 📋 Folder Structure

```
clause-rag-v1/
├── context/                          ← You are here
│   ├── README.md                     ← This file
│   ├── 01-PROJECT-OVERVIEW.md
│   ├── 02-INFRASTRUCTURE.md
│   ├── 03-INGESTION-PIPELINE.md
│   ├── 04-INDEXING.md
│   ├── 05-RETRIEVAL-PIPELINE.md
│   ├── 06-AGENT-LOOP.md
│   ├── 07-GENERATION-CITATIONS.md
│   ├── 08-EVALUATION.md
│   ├── 09-API-FRONTEND.md
│   ├── 10-DATA-MODELS.md
│   ├── 11-GRAPH-SCHEMA.md
│   ├── 12-PROMPTS.md
│   └── 13-CONSTRAINTS.md
├── clause/                           ← Main Python package
├── data/                             ← Raw, processed, eval data
├── notebooks/                        ← Exploration (not production code)
├── scripts/                          ← CLI entry points
├── frontend/                         ← Streamlit app
├── tests/                            ← Unit & integration tests
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md                         ← Project setup & usage
```

---

## 🔒 Key Principles

1. **Architecture is locked** — Don't propose alternatives to core decisions
2. **Every component has a reason** — Read the "Why" sections in each doc
3. **Tech stack is non-negotiable** — See [13-CONSTRAINTS.md](13-CONSTRAINTS.md)
4. **Modular design** — Each pipeline step is independent and testable
5. **Quality metrics** — RAGAS evaluation proves system quality

---

## 📖 Reading Order Recommendations

### For New Team Members
1. [01-PROJECT-OVERVIEW.md](01-PROJECT-OVERVIEW.md) — Understand the project
2. [02-INFRASTRUCTURE.md](02-INFRASTRUCTURE.md) — Set up local environment
3. [03-INGESTION-PIPELINE.md](03-INGESTION-PIPELINE.md) — Understand data flow
4. [13-CONSTRAINTS.md](13-CONSTRAINTS.md) — Know what NOT to do

### For Implementation
1. Read relevant pipeline doc (e.g., [05-RETRIEVAL-PIPELINE.md](05-RETRIEVAL-PIPELINE.md))
2. Check data models in [10-DATA-MODELS.md](10-DATA-MODELS.md)
3. Reference Neo4j schema in [11-GRAPH-SCHEMA.md](11-GRAPH-SCHEMA.md) if needed
4. Check constraints in [13-CONSTRAINTS.md](13-CONSTRAINTS.md)

### For Evaluation
1. Read [08-EVALUATION.md](08-EVALUATION.md) to understand metrics
2. Review [01-PROJECT-OVERVIEW.md](01-PROJECT-OVERVIEW.md) for ablation strategy

---

**Document version: 1.0** | **Status: Architecture locked — implementation in progress**

