# 01 — Project Overview & Architecture

## 1. Project Identity

| Field | Value |
|---|---|
| **Product Name** | Clause |
| **Tagline** | *"Legal clarity for Indian startups"* |
| **Domain** | Indian Startup & Corporate Law |
| **Architecture** | Hybrid GraphRAG + Agentic Loop |
| **Primary Corpus** | Companies Act 2013, MCA Rules, SEBI Regulations, DPIIT Guidelines |
| **Goal** | Resume-grade ML engineering project demonstrating state-of-the-art RAG |
| **Target Users** | Indian startup founders, CAs, corporate lawyers, compliance officers |

---

## 2. System Architecture

### Full Pipeline — End to End

```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION PIPELINE                        │
│                                                                   │
│  PDFs/HTMLs → Parse → Chunk → Contextualize → Embed → Index     │
│                                    │                              │
│                              Neo4j Graph                          │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                         QUERY PIPELINE                           │
│                                                                   │
│  User Query                                                       │
│      │                                                            │
│      ▼                                                            │
│  Query Processor                                                  │
│  ├── Query Classification (simple / multi-hop / cross-doc)       │
│  ├── Query Expansion (→ 3 sub-queries for better recall)         │
│  └── HyDE (generate hypothetical answer → embed → search)        │
│      │                                                            │
│      ├──────────────────────┐                                     │
│      ▼                      ▼                                     │
│  Dense Retrieval        Sparse Retrieval                          │
│  (Qdrant vector)        (BM25s keyword)                          │
│      │                      │                                     │
│      └──────────┬───────────┘                                     │
│                 ▼                                                  │
│          RRF Fusion (top-20)                                      │
│                 │                                                  │
│                 ▼                                                  │
│          Cohere Reranker (top-20 → top-5)                        │
│                 │                                                  │
│                 ▼                                                  │
│          Parent Chunk Fetch (child → parent context)              │
│                 │                                                  │
│                 ▼                                                  │
│          Graph Augmentation (Neo4j traversal)                     │
│          ├── Entity lookup from retrieved chunks                  │
│          ├── Relationship traversal (2-hop max)                   │
│          └── Merge graph context with vector context              │
│                 │                                                  │
│                 ▼                                                  │
│          LangGraph Agentic Loop                                   │
│          ├── CRAG Check: is context sufficient?                   │
│          │   ├── YES → proceed to generation                      │
│          │   └── NO → re-retrieve with refined query              │
│          ├── Multi-hop reasoning if needed                        │
│          └── Max 3 iterations                                     │
│                 │                                                  │
│                 ▼                                                  │
│          LLM Generation (Claude Sonnet)                           │
│          └── Answer + inline section citations                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

| Layer | Technology | Version | Status |
|---|---|---|---|
| Language | Python | 3.11+ | ✅ |
| LLM — Generation | Claude Sonnet / Ollama qwen2.5:7b | latest | ⬜ generation / ✅ enrichment done |
| LLM — Contextualization | Ollama qwen2.5:7b (local, free) | 7b | ✅ Done |
| Embeddings | BAAI/bge-large-en-v1.5 (local, free) | HuggingFace | ✅ Done |
| Vector DB | Qdrant | 1.18.1 | ✅ Running |
| Sparse Search | rank-bm25 (BM25Okapi) | 0.2.2 | ✅ Done |
| Graph DB | Neo4j | 5.20.0 Community | ✅ Running |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 (local, free) | HuggingFace | ✅ Done |
| Document Parsing | unstructured[pdf] + pdfplumber | latest | ✅ Done |
| Table Extraction | pdfplumber + camelot | latest | ✅ Done |
| HTML Parsing | BeautifulSoup4 | latest | ✅ Done |
| Orchestration | LangGraph | latest | ⬜ Pending |
| Evaluation | ragas | latest | ⬜ Pending |
| API | FastAPI | latest | ⬜ Pending |
| Frontend | Streamlit | latest | ⬜ Pending |
| Infra | Docker Compose (v2) | latest | ✅ Running |
| Config | pydantic-settings | 2.1.0 | ✅ Done |

---

## 4. Folder Structure

```
clause/
├── ARCHITECTURE.md                     ← THIS FILE — read before any code
├── CONTEXT.md                          ← Project context and identity
├── README.md                           ← Setup, usage, results
├── .env                                ← Never commit — actual secrets
├── .env.example                        ← Commit this — template only
├── .gitignore
├── docker-compose.yml                  ← Qdrant + Neo4j services
├── pyproject.toml                      ← Project metadata + deps
├── requirements.txt                    ← Pinned deps for reproducibility
│
├── data/
│   ├── raw/                            ← Downloaded source PDFs/HTMLs — never modify
│   │   ├── companies_act/
│   │   │   ├── companies_act_2013.pdf
│   │   │   └── amendment_2020.pdf
│   │   ├── rules/
│   │   │   ├── incorporation_rules_2014.pdf
│   │   │   ├── share_capital_rules_2014.pdf
│   │   │   ├── accounts_rules_2014.pdf
│   │   │   ├── meetings_rules_2014.pdf
│   │   │   └── directors_rules_2014.pdf
│   │   ├── sebi/
│   │   │   ├── icdr_2018.pdf
│   │   │   └── aif_2012.pdf
│   │   ├── dpiit/
│   │   │   └── startup_recognition_guidelines.pdf
│   │   └── income_tax/
│   │       └── section_80iac.pdf
│   │
│   ├── processed/
│   │   ├── parsed/                     ← Raw text extracted from PDFs
│   │   ├── chunks/                     ← LegalChunk JSONs post-chunking
│   │   ├── enriched/                   ← LegalChunk JSONs post-contextualization
│   │   └── graph/                      ← Entity/relation JSONs for Neo4j import
│   │
│   └── eval/
│       ├── questions.json              ← 20 curated eval questions
│       ├── ground_truth.json           ← Expert-written reference answers
│       └── results/                    ← RAGAS output JSONs per variant
│
├── clause/                             ← Main Python package
│   ├── __init__.py
│   ├── config.py                       ← Pydantic settings, all env vars
│   │
│   ├── ingestion/                      ← Full ingestion pipeline
│   │   ├── __init__.py
│   │   ├── pipeline.py                 ← Orchestrates steps 1-6 end to end
│   │   │
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py           ← unstructured + pdfplumber
│   │   │   ├── html_parser.py          ← BeautifulSoup for India Code HTML
│   │   │   └── table_extractor.py      ← camelot for penalty/fee tables
│   │   │
│   │   ├── chunkers/
│   │   │   ├── __init__.py
│   │   │   ├── section_chunker.py      ← Primary: regex-based legal section splitter
│   │   │   └── hierarchical_chunker.py ← Parent-child chunk assembly
│   │   │
│   │   ├── enrichment/
│   │   │   ├── __init__.py
│   │   │   └── contextualizer.py       ← Async LLM calls to prepend context
│   │   │
│   │   └── extractors/
│   │       ├── __init__.py
│   │       ├── entity_extractor.py     ← LLM-based NER for legal entities
│   │       ├── relation_extractor.py   ← Extract typed relationships
│   │       └── cross_ref_resolver.py   ← Resolve "section 2(68)" → node ID
│   │
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── vector_store.py             ← Qdrant collection management + upsert
│   │   ├── bm25_index.py               ← BM25s index build, persist, search
│   │   └── graph_store.py              ← Neo4j session, node/edge upsert
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── dense_retriever.py          ← Qdrant vector search
│   │   ├── sparse_retriever.py         ← BM25s search
│   │   ├── hybrid_retriever.py         ← RRF fusion of dense + sparse
│   │   ├── reranker.py                 ← Cohere Rerank v3
│   │   ├── parent_fetcher.py           ← Child chunk ID → parent chunk text
│   │   ├── graph_retriever.py          ← Neo4j traversal queries
│   │   └── hyde.py                     ← Hypothetical Document Embedding
│   │
│   ├── query/
│   │   ├── __init__.py
│   │   ├── classifier.py               ← Classify: simple / multi-hop / cross-doc
│   │   └── expander.py                 ← Expand 1 query → 3 sub-queries
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── schema.py                   ← Node + edge type constants
│   │   ├── builder.py                  ← Orchestrates entity → Neo4j pipeline
│   │   ├── traversal.py                ← Multi-hop Cypher query logic
│   │   └── cypher_templates.py         ← All Cypher queries as named constants
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py                    ← TypedDict for LangGraph state
│   │   ├── nodes.py                    ← Node functions: retrieve, check, generate
│   │   ├── edges.py                    ← Conditional edge routing logic
│   │   ├── graph.py                    ← StateGraph assembly + compilation
│   │   └── tools.py                    ← LangGraph tools for agent
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── prompts.py                  ← ALL prompt templates as constants
│   │   └── generator.py                ← LLM call + citation extraction
│   │
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── ragas_eval.py               ← RAGAS metric computation
│   │   ├── benchmark.py                ← Run all 3 variants, compare
│   │   └── dataset_builder.py          ← Curate eval Q&A dataset
│   │
│   └── api/
│       ├── __init__.py
│       ├── main.py                     ← FastAPI app factory
│       ├── routes/
│       │   ├── query.py                ← POST /query
│       │   └── ingest.py               ← POST /ingest (trigger pipeline)
│       ├── schemas.py                  ← Request/response Pydantic models
│       └── middleware.py               ← CORS, logging, error handling
│
├── frontend/
│   └── app.py                          ← Streamlit demo UI
│
├── notebooks/
│   ├── 01_data_exploration.ipynb       ← Inspect raw PDFs, chunk distribution
│   ├── 02_graph_construction.ipynb     ← Visualize Neo4j graph, validate entities
│   ├── 03_retrieval_experiments.ipynb  ← Compare dense vs hybrid vs graph retrieval
│   └── 04_evaluation_results.ipynb     ← RAGAS scores, ablation table (show to interviewers)
│
├── scripts/
│   ├── run_ingestion.py                ← CLI: run full pipeline on data/raw/
│   ├── run_eval.py                     ← CLI: run RAGAS benchmark
│   └── inspect_graph.py               ← CLI: print graph stats
│
└── tests/
    ├── conftest.py                     ← Shared fixtures
    ├── test_parsers.py
    ├── test_chunkers.py
    ├── test_contextualizer.py
    ├── test_retrieval.py
    ├── test_graph.py
    └── test_api.py
```

---

## 5. Implementation Status

| Step | Description | Status | Output |
|---|---|---|---|
| Step 1 | Document Parsing (PDF + HTML + Tables) | ✅ Complete | 10 documents parsed |
| Step 2 | Hierarchical Chunking (parent/child/table) | ✅ Complete | 13,987 chunks created |
| Step 3 | Contextual Enrichment (Ollama qwen2.5:7b) | ✅ Complete | 7,367 child chunks enriched |
| Step 4 | Vector Indexing (BGE → Qdrant) | ✅ Complete | 7,549 points @ 1024 dims |
| Step 5 | BM25 Sparse Indexing | ✅ Complete | 7,549 chunks → bm25_index.pkl |
| Step 6 | Knowledge Graph (Neo4j) | ✅ Complete | 12,568 nodes, 28,859 edges |
| Step 7 | Hybrid Retrieval (Vector + BM25 + Graph + Reranker) | ✅ Complete | Tested and working |
| Step 8 | Answer Generation | ⬜ Next | — |
| Step 9 | API (FastAPI) | ⬜ Pending | — |
| Step 10 | Frontend (Streamlit) | ⬜ Pending | — |

---

## 6. Key Design Decisions Made

| Decision | Original Plan | Actual Implementation | Reason |
|---|---|---|---|
| Enrichment LLM | Claude Haiku (API) | Ollama qwen2.5:7b (local) | No API key |
| Embedding model | OpenAI text-embedding-3-large (3072 dims) | BAAI/bge-large-en-v1.5 (1024 dims) | No API key — local/free |
| Reranker | Cohere Rerank v3 (API) | cross-encoder/ms-marco-MiniLM-L-6-v2 (local) | No API key |
| Docker Compose | v1 (`docker-compose`) | v2 (`docker compose`) | v1 broken with urllib3 v2 |

---

## 🔗 Next Steps

- Infrastructure setup: [02-INFRASTRUCTURE.md](02-INFRASTRUCTURE.md)
- Ingestion pipeline: [03-INGESTION-PIPELINE.md](03-INGESTION-PIPELINE.md)
- Indexing: [04-INDEXING.md](04-INDEXING.md)
- Retrieval pipeline: [05-RETRIEVAL-PIPELINE.md](05-RETRIEVAL-PIPELINE.md)
- Generation: [07-GENERATION-CITATIONS.md](07-GENERATION-CITATIONS.md)
