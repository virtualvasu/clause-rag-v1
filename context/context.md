# Clause — Project Context & Technical Blueprint

> **This file is the source of truth for the Clause project.**
> Claude Code must read this before writing any code, making any architectural decision, or suggesting any deviation from the plan. Do not deviate from this document without explicit user approval.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Product Name** | Clause |
| **Tagline** | *"Legal clarity for Indian startups"* |
| **Domain** | Indian Startup & Corporate Law |
| **Type** | Enterprise-grade RAG system with Knowledge Graph |
| **Goal** | Resume-grade ML/AI engineering project + potential product |
| **Target Users** | Indian startup founders, CAs, corporate lawyers, compliance officers |

---

## 2. Problem Statement

Indian startup founders and lawyers need answers to complex, multi-hop legal questions like:

- *"What are compliance requirements for a private limited company with 3 foreign directors in its first year?"*
- *"What changed for ESOP taxation between 2020 and 2023?"*
- *"Which SEBI regulations apply to a startup raising a Series B from a US VC?"*

Baseline RAG (vector search only) **fails** at these queries because they require:
- Traversing relationships across multiple sections and acts
- Conditional logic (`IF entity_type == small_company AND turnover < 50Cr THEN...`)
- Temporal reasoning (amendment histories, effective dates)
- Cross-document linking (SEBI regulation → issued under → Companies Act section)

Clause solves this using **Hybrid GraphRAG** — combining vector search, BM25, a Neo4j knowledge graph, and an agentic reasoning loop.

---

## 3. Architecture Overview

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│        Query Processor          │
│  - Query classification         │
│  - HyDE (Hypothetical Doc Emb)  │
│  - Query expansion              │
└────────────┬────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌──────────┐    ┌──────────────┐
│  Vector  │    │     BM25     │
│  Search  │    │ Sparse Search│
│ (Qdrant) │    │  (BM25s)     │
└────┬─────┘    └──────┬───────┘
     │                 │
     └────────┬────────┘
              │ Reciprocal Rank Fusion (RRF)
              ▼
     ┌─────────────────┐
     │    Reranker      │
     │  (Cohere v3 /   │
     │   ColBERT)       │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Knowledge Graph │
     │  Retrieval       │
     │  (Neo4j)         │
     │  - Entity lookup │
     │  - Graph traversal│
     │  - Path reasoning│
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Agentic Loop   │
     │  (LangGraph)    │
     │  - CRAG check   │
     │  - Re-retrieve  │
     │  - Multi-hop    │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │   LLM Generator │
     │  (Claude/GPT-4o)│
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │    Response +   │
     │    Citations    │
     │  (Section refs) │
     └─────────────────┘
```

---

## 4. Tech Stack (Locked — Do Not Change Without Approval)

| Layer | Technology | Reason |
|---|---|---|
| **Language** | Python 3.11+ | Standard for ML projects |
| **Orchestration** | LangGraph | Agentic loops, state machines |
| **LLM** | Claude Sonnet (primary), GPT-4o (fallback) | Via Anthropic + OpenAI SDK |
| **Embeddings** | `text-embedding-3-large` (OpenAI) or `BGE-M3` (local) | High quality multilingual |
| **Vector DB** | Qdrant (self-hosted via Docker) | Production-grade, free, fast |
| **Sparse Search** | BM25s (Python library) | Lightweight BM25 for hybrid |
| **Graph DB** | Neo4j (Docker / AuraDB free tier) | Industry standard for knowledge graphs |
| **Reranker** | Cohere Rerank v3 | Best quality reranker available via API |
| **Document Parsing** | `unstructured.io` + `pdfplumber` + `camelot` | Handles PDFs, tables, section headers |
| **Evaluation** | RAGAS | Faithfulness, relevancy, context precision |
| **Tracing** | LangSmith | Full pipeline observability |
| **API Layer** | FastAPI | REST endpoints for query + ingest |
| **Frontend** | Streamlit (demo) | Fast to build, good enough for demo |
| **Infra** | Docker + Docker Compose | Reproducible local setup |
| **CI** | GitHub Actions | Linting, tests, basic checks |

---

## 5. Knowledge Graph Schema (Neo4j)

### Node Types

```cypher
// Legal Documents
(:Act {name, year, ministry, status, source_url})
(:Section {number, title, text, act_name, chapter})
(:Rule {number, title, text, parent_act, rule_set_name})
(:Regulation {number, title, text, issuing_authority})
(:Amendment {year, act_amended, description, effective_date})
(:Notification {number, date, issuing_authority, subject})

// Legal Concepts
(:Definition {term, definition_text, defined_in_section})
(:ComplianceObligation {name, description, frequency, due_date_logic})
(:Penalty {amount_min, amount_max, type, currency})
(:Offense {name, description, section_reference})
(:Exemption {description, condition, applies_to})

// Business Entities
(:EntityType {name}) // e.g. PrivateLimited, LLP, OPC, PublicLimited
(:Threshold {metric, value, unit}) // e.g. turnover < 50Cr
(:Authority {name, type}) // e.g. MCA, SEBI, RBI, NCLT
```

### Relationship Types

```cypher
(Section)-[:PART_OF]->(Act)
(Rule)-[:ISSUED_UNDER]->(Section)
(Regulation)-[:ISSUED_UNDER]->(Act)
(Section)-[:AMENDED_BY]->(Amendment)
(Section)-[:CROSS_REFERENCES]->(Section)
(Section)-[:DEFINES]->(Definition)
(ComplianceObligation)-[:GOVERNED_BY]->(Section)
(ComplianceObligation)-[:APPLIES_TO]->(EntityType)
(ComplianceObligation)-[:HAS_CONDITION]->(Threshold)
(ComplianceObligation)-[:PENALTY_FOR_BREACH]->(Penalty)
(ComplianceObligation)-[:ENFORCED_BY]->(Authority)
(Offense)-[:PUNISHABLE_UNDER]->(Section)
(Offense)-[:CARRIES_PENALTY]->(Penalty)
(EntityType)-[:EXEMPT_FROM]->(ComplianceObligation)
```

---

## 6. Corpus (Data Sources)

### Phase 1 — Must Have (Build this first)

| Document | Source | Format |
|---|---|---|
| Companies Act 2013 + amendments | indiacode.nic.in | HTML/PDF |
| Companies (Incorporation) Rules 2014 | mca.gov.in | PDF |
| Companies (Share Capital) Rules 2014 | mca.gov.in | PDF |
| Companies (Accounts) Rules 2014 | mca.gov.in | PDF |
| Companies (Meetings) Rules 2014 | mca.gov.in | PDF |
| Companies (Directors) Rules 2014 | mca.gov.in | PDF |
| SEBI (ICDR) Regulations 2018 | sebi.gov.in | PDF |
| SEBI (AIF) Regulations 2012 | sebi.gov.in | PDF |
| DPIIT Startup Recognition Guidelines | dpiit.gov.in | PDF |
| Startup India Tax Exemption (80IAC) | incometaxindia.gov.in | PDF |

### Phase 2 — Add After Phase 1 Works

| Document | Source |
|---|---|
| IBC 2016 (Insolvency & Bankruptcy Code) | indiacode.nic.in |
| FEMA 1999 + FDI Master Direction | rbi.org.in |
| SEBI (PIT) Regulations 2015 | sebi.gov.in |
| LLP Act 2008 + LLP Rules 2009 | mca.gov.in |

### Phase 3 — Stretch Goals

| Document | Source |
|---|---|
| DPDP Act 2023 | indiacode.nic.in |
| IT Act 2000 (relevant sections) | indiacode.nic.in |
| Competition Act 2002 | indiacode.nic.in |

---

## 7. Project Folder Structure

```
clause/
├── CONTEXT.md                          ← THIS FILE
├── README.md
├── .env.example
├── docker-compose.yml                  ← Qdrant + Neo4j + API
├── pyproject.toml
├── requirements.txt
│
├── data/
│   ├── raw/                            ← Downloaded source PDFs/HTMLs
│   │   ├── companies_act/
│   │   ├── rules/
│   │   ├── sebi/
│   │   ├── dpiit/
│   │   └── fema/
│   ├── processed/
│   │   ├── chunks/                     ← Chunked text JSONs
│   │   ├── entities/                   ← Extracted entity JSONs
│   │   └── graph/                      ← Graph import CSVs
│   └── eval/
│       ├── questions.json              ← 20 curated eval questions
│       └── ground_truth.json
│
├── clause/                             ← Main Python package
│   ├── __init__.py
│   │
│   ├── ingestion/                      ← Data pipeline
│   │   ├── __init__.py
│   │   ├── parsers/
│   │   │   ├── pdf_parser.py           ← unstructured + pdfplumber
│   │   │   ├── html_parser.py          ← BeautifulSoup for indiacode
│   │   │   └── table_extractor.py      ← camelot for penalty tables
│   │   ├── chunkers/
│   │   │   ├── hierarchical_chunker.py ← Parent-child chunks
│   │   │   └── section_chunker.py      ← Section-aware splitting
│   │   ├── extractors/
│   │   │   ├── entity_extractor.py     ← LLM-based NER for legal entities
│   │   │   ├── relation_extractor.py   ← Extract relationships for graph
│   │   │   └── section_linker.py       ← Resolve cross-references
│   │   └── pipeline.py                 ← Orchestrates full ingestion
│   │
│   ├── indexing/                       ← Store into DBs
│   │   ├── __init__.py
│   │   ├── vector_store.py             ← Qdrant operations
│   │   ├── bm25_index.py               ← BM25s index build + search
│   │   └── graph_store.py              ← Neo4j operations
│   │
│   ├── retrieval/                      ← Retrieval strategies
│   │   ├── __init__.py
│   │   ├── dense_retriever.py          ← Vector search
│   │   ├── sparse_retriever.py         ← BM25 search
│   │   ├── hybrid_retriever.py         ← RRF fusion
│   │   ├── graph_retriever.py          ← Neo4j traversal
│   │   ├── reranker.py                 ← Cohere reranker
│   │   └── hyde.py                     ← HyDE query expansion
│   │
│   ├── graph/                          ← Knowledge graph logic
│   │   ├── __init__.py
│   │   ├── schema.py                   ← Node/edge type definitions
│   │   ├── builder.py                  ← Build graph from entities
│   │   ├── traversal.py                ← Multi-hop path queries
│   │   └── cypher_templates.py         ← Reusable Cypher queries
│   │
│   ├── agent/                          ← LangGraph agentic loop
│   │   ├── __init__.py
│   │   ├── state.py                    ← LangGraph state definition
│   │   ├── nodes.py                    ← Graph node functions
│   │   ├── edges.py                    ← Conditional routing logic
│   │   ├── graph.py                    ← LangGraph graph assembly
│   │   └── tools.py                    ← Agent tools (retrieve, graph_query)
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── prompts.py                  ← All prompt templates
│   │   └── generator.py                ← LLM call + citation formatting
│   │
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── ragas_eval.py               ← RAGAS metrics
│   │   ├── benchmark.py                ← Compare naive vs hybrid vs graph
│   │   └── dataset_builder.py          ← Build eval Q&A pairs
│   │
│   └── api/
│       ├── __init__.py
│       ├── main.py                     ← FastAPI app
│       ├── routes/
│       │   ├── query.py                ← POST /query
│       │   └── ingest.py               ← POST /ingest
│       └── schemas.py                  ← Pydantic models
│
├── frontend/
│   └── app.py                          ← Streamlit demo UI
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_graph_construction.ipynb
│   ├── 03_retrieval_experiments.ipynb
│   └── 04_evaluation_results.ipynb     ← THIS is what you show interviewers
│
├── scripts/
│   ├── download_corpus.py              ← Automated corpus download
│   ├── run_ingestion.py                ← Full pipeline trigger
│   └── run_eval.py                     ← Evaluation runner
│
└── tests/
    ├── test_parsers.py
    ├── test_retrieval.py
    ├── test_graph.py
    └── test_api.py
```

---

## 8. Build Phases & Milestones

### Phase 1 — Foundation (Weeks 1–2)
**Goal**: End-to-end RAG working over Companies Act

- [ ] Download + parse Companies Act 2013 (HTML from indiacode)
- [ ] Build hierarchical chunker (parent-child chunks)
- [ ] Embed chunks → Qdrant
- [ ] BM25 index built
- [ ] Basic hybrid retrieval (RRF) working
- [ ] Cohere reranker integrated
- [ ] FastAPI `/query` endpoint returning answers with section citations
- [ ] **Milestone**: Answer "What is the process to incorporate a private limited company?" correctly with citations

### Phase 2 — Knowledge Graph (Weeks 3–4)
**Goal**: Neo4j graph built, multi-hop queries working

- [ ] Entity extractor (sections, obligations, penalties, entity types)
- [ ] Relation extractor (cross-references, issued-under, applies-to)
- [ ] Neo4j graph populated from Companies Act
- [ ] Graph traversal retriever working
- [ ] HyDE implemented for abstract queries
- [ ] **Milestone**: Answer "What are penalties for a director of a small company failing to file annual returns?" using graph traversal

### Phase 3 — Full Corpus + Agentic Loop (Week 5)
**Goal**: SEBI + DPIIT corpus added, LangGraph agent working

- [ ] SEBI ICDR + AIF parsed and indexed
- [ ] DPIIT startup guidelines indexed
- [ ] Cross-document graph edges built (SEBI regulation → Companies Act section)
- [ ] LangGraph agentic loop: plan → retrieve → CRAG check → re-retrieve → generate
- [ ] Adaptive query routing (simple → hybrid RAG, complex → graph + agent)
- [ ] **Milestone**: Answer "What SEBI regulations apply to a startup raising Series B from a US VC, and which Companies Act sections govern the share allotment?"

### Phase 4 — Evaluation + Production Polish (Week 6)
**Goal**: Quantified results, production-ready repo

- [ ] 20 curated eval questions with ground truth answers
- [ ] RAGAS evaluation: faithfulness, answer relevancy, context precision, context recall
- [ ] Benchmark: Naive RAG vs Hybrid RAG vs GraphRAG on all 20 questions
- [ ] LangSmith tracing integrated
- [ ] Docker Compose with all services (Qdrant + Neo4j + API)
- [ ] Streamlit demo UI
- [ ] Clean README with architecture diagram, results table, setup instructions
- [ ] Notebooks with evaluation results and ablation study
- [ ] **Milestone**: Show X% improvement of GraphRAG over naive RAG on multi-hop questions

---

## 9. Evaluation Strategy

### RAGAS Metrics (Primary)
| Metric | What It Measures | Target |
|---|---|---|
| **Faithfulness** | Answer is grounded in retrieved context | > 0.85 |
| **Answer Relevancy** | Answer actually addresses the question | > 0.80 |
| **Context Precision** | Retrieved chunks are relevant | > 0.75 |
| **Context Recall** | All necessary info was retrieved | > 0.70 |

### Ablation Benchmark (The Resume Story)
Run all 20 eval questions through 3 system variants and record scores:

| System Variant | Description |
|---|---|
| **Naive RAG** | Chunk → embed → top-k → generate |
| **Advanced RAG** | Hybrid (dense+BM25) + reranker + HyDE |
| **Clause (GraphRAG)** | Advanced RAG + Knowledge Graph + Agentic loop |

**This table is the centrepiece of your resume talking point.**

### Eval Question Categories (20 total)
- 5 simple single-section lookups (naive RAG should handle)
- 5 multi-section reasoning questions
- 5 cross-act questions (Companies Act + SEBI)
- 5 complex multi-hop with conditions (only GraphRAG should handle well)

---

## 10. Key Design Decisions & Rationale

### Why Hierarchical Chunking?
Small chunks (256 tokens) for precise retrieval. Parent chunks (1024 tokens) sent to LLM for full context. Avoids the "retrieved chunk cuts off mid-section" problem.

### Why Both Vector + BM25?
Legal text has exact terminology (`Section 42`, `Form MGT-7`, `DIN`). Pure vector search misses exact matches. BM25 catches them. RRF fusion gets the best of both.

### Why Neo4j over in-memory graph?
Cross-document relationships need persistent, queryable graph. Cypher queries are far more expressive than manual graph traversal. Also — Neo4j on resume is a signal.

### Why LangGraph over LangChain LCEL?
Agentic loops with conditional routing and state management are cleaner in LangGraph. The CRAG pattern (evaluate → re-retrieve if poor) requires a real state machine.

### Why Cohere Reranker?
Cross-encoder rerankers dramatically improve precision@k. Cohere v3 is the best API-available reranker without running your own model.

### Why RAGAS?
It's the industry standard for RAG evaluation. Listing "evaluated with RAGAS, achieving 0.87 faithfulness" on a resume is concrete and credible.

---

## 11. What Claude Code Must NOT Do

- Do not swap Qdrant for another vector DB without approval
- Do not replace LangGraph with a simpler chain — the agentic loop is a core feature
- Do not skip the BM25 component — hybrid retrieval is non-negotiable
- Do not skip RAGAS evaluation — the benchmark numbers are the point
- Do not add new corpus domains (e.g. criminal law, family law) to Phase 1 or 2
- Do not use LangChain's built-in RAG chains — build retrievers modularly
- Do not put all logic in notebooks — notebooks are for exploration only, production code lives in `clause/`
- Do not use ChromaDB or FAISS — Qdrant is the chosen vector store
- Do not change the folder structure without updating this file

---

## 12. Environment Variables (.env)

```bash
# LLM
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=clause_chunks

# Graph DB
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=

# Reranker
COHERE_API_KEY=

# Observability
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=clause

# Config
EMBEDDING_MODEL=text-embedding-3-large
LLM_MODEL=claude-sonnet-4-20250514
TOP_K_RETRIEVAL=20
TOP_K_RERANK=5
CHUNK_SIZE=256
PARENT_CHUNK_SIZE=1024
```


