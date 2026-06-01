# Clause — Hybrid GraphRAG for Indian Legal Documents

3-layer hierarchical chunking for legal documents with parent-child relationships.

## Chunking Specification

### Layer 1: Document Chunk
- **Definition:** Document metadata wrapper
- **Size:** Minimal (~10-50 tokens)
- **ID Format:** `ACT_DOC` (e.g., `CA2013_DOC`)
- **Fields:** act, name, year, ministry, total_sections, source_file

### Layer 2: Parent Chunk (Section-Level)
- **Definition:** Complete legal section from heading to all subsections, provisos, explanations
- **Size:** 512–1024 tokens (enforced via tiktoken cl100k_base)
- **ID Format:** `ACT_S{n}` (e.g., `CA2013_S42`)
- **Metadata:** section_number, text, children_ids, source_page, tokens

### Layer 3: Child Chunk (Subsection-Level)
- **Definition:** Individual subsection (1), (2), (3), proviso, or explanation
- **Size:** 128–256 tokens (enforced via tiktoken cl100k_base)
- **ID Format:** `ACT_S{n}_{m}` (e.g., `CA2013_S42_1`)
- **Metadata:** parent_id, section_number, text, tokens, sentence_window (±2 sentences)

## Special Handling

| Element | Strategy |
|---------|----------|
| **Proviso** | Merged with parent section (not split) |
| **Explanation** | Merged with parent section (not split) |
| **Cross-References** | Detected via regex, stored in chunk, creates Neo4j edges |
| **Tables** | Preserved as atomic chunks, parsed to structured list |
| **Sentence Window** | ±2 sentences attached to child chunks for context |

## Pipeline Output

**Documents Processed:** 9/10  
**Total Chunks:** 5,708 (9 document + 2,878 parent + 2,821 child)  
**Output Location:** `data/processed/chunks/*.json`  
**Relationships:** `data/processed/graph/relationships.csv` (5,643 edges)  
**Summary Report:** `data/processed/entities/SUMMARY.md`

## Implementation

- **Engine:** [clause/ingestion/chunkers/section_chunker.py](clause/ingestion/chunkers/section_chunker.py) (SectionChunker class)
- **Orchestrator:** [clause/ingestion/pipeline.py](clause/ingestion/pipeline.py) (IngestionPipeline class)
- **Model:** Pydantic LegalChunk with 15 fields
- **Token Counting:** tiktoken (cl100k_base encoding)

## Chunk Format

Each chunk is a JSON file with this structure:

```json
{
  "chunk_id": "CA2013_S42_1",
  "type": "child",
  "text": "Every company shall have at least one director...",
  "act": "CA2013",
  "section_number": "42",
  "section_title": "Appointment of directors",
  "parent_id": "CA2013_S42",
  "children_ids": [],
  "tokens": 142,
  "sentence_window": "Full section with surrounding context...",
  "cross_references": ["Section 2(34)", "Rule 4"],
  "source_file": "Companies_Act_2013.pdf",
  "source_page": null,
  "name": "Companies Act 2013",
  "year": 2013,
  "ministry": "Ministry of Corporate Affairs",
  "source_url": null,
  "total_sections": 465,
  "structured": null
}
```

## Documents Included

1. Companies Act 2013 (CA2013)
2. Companies Incorporation Rules 2014 (CIR2014)
3. Companies Share Capital Rules 2014 (CSCR2014)
4. Companies Accounts Rules 2014 (CAR2014)
5. Companies Meetings Rules 2014 (CMR2014)
6. Companies Directors Rules 2014 (CDR2014)
7. SEBI ICDR Regulations 2018 (SEBI_ICDR2018)
8. SEBI AIF Regulations 2012 (SEBI_AIF2012)
9. DPIIT Startup Recognition Guidelines (DPIIT_SRG)

## Next Steps

- Embed child chunks to Qdrant (vector indexing)
- Import relationships.csv to Neo4j (knowledge graph)
- Build BM25 sparse index
- Connect retrieval pipeline
├── docker-compose.yml                 ← Services: Qdrant, Neo4j, API
├── Dockerfile.api                     ← FastAPI container
├── requirements.txt                   ← Python dependencies
├── .env.example                       ← Environment template
├── qdrant_config.yaml                 ← Qdrant settings
│
├── data/
│   ├── raw/                           ← Source PDFs/HTMLs (your corpus)
│   │   ├── companies_act/
│   │   ├── companies_rules/
│   │   ├── sebi/
│   │   ├── dpiit/
│   │   └── startup_tax/
│   ├── processed/
│   │   ├── chunks/                    ← OUTPUT: Extracted chunks (JSON)
│   │   ├── entities/                  ← OUTPUT: Entity metadata
│   │   └── graph/                     ← OUTPUT: Neo4j import CSVs
│   └── eval/
│       ├── questions.json             ← Test questions
│       └── ground_truth.json          ← Expected answers
│
├── clause/                            ← Main Python package
│   ├── __init__.py
│   ├── ingestion/                     ← Data pipeline (Phase 2)
│   │   ├── __init__.py
│   │   ├── parsers/
│   │   │   ├── pdf_parser.py          ← PDF extraction
│   │   │   ├── html_parser.py         ← HTML extraction
│   │   │   └── table_extractor.py     ← Table extraction
│   │   ├── chunkers/
│   │   │   ├── hierarchical_chunker.py
│   │   │   ├── special_elements.py    ← Definitions, penalties, tables
│   │   │   └── metadata_enricher.py
│   │   └── pipeline.py                ← Main orchestrator
│   │
│   ├── indexing/                      ← Database operations (Phase 3)
│   │   ├── vector_store.py
│   │   ├── bm25_index.py
│   │   └── graph_store.py
│   │
│   ├── retrieval/                     ← Search & ranking (Phase 4-6)
│   │   ├── dense_retriever.py
│   │   ├── sparse_retriever.py
│   │   ├── hybrid_retriever.py
│   │   ├── graph_retriever.py
│   │   ├── reranker.py
│   │   └── hyde.py
│   │
│   ├── graph/                         ← Knowledge graph (Phase 5)
│   │   ├── schema.py
│   │   ├── builder.py
│   │   ├── traversal.py
│   │   └── cypher_templates.py
│   │
│   ├── agent/                         ← Agentic loop (Phase 7)
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── edges.py
│   │   ├── graph.py
│   │   └── tools.py
│   │
│   ├── generation/                    ← LLM generation (Phase 8)
│   │   ├── prompts.py
│   │   └── generator.py
│   │
│   ├── evaluation/                    ← RAGAS metrics (Phase 9)
│   │   ├── ragas_eval.py
│   │   ├── benchmark.py
│   │   └── dataset_builder.py
│   │
│   └── api/                           ← REST API (Phase 10)
│       ├── __init__.py
│       ├── main.py
│       └── routes/
│           ├── __init__.py
│           ├── query.py
│           └── ingest.py
│
└── diagrams/                          ← Architecture diagrams (SVG)
    ├── 01-system-architecture.svg
    ├── 02-chunking-strategy.svg
    └── 03-data-flow.svg
```

---

## Running the Pipeline

### Phase 1: PDF Parsing & Chunking

```bash
# Activate virtual environment
source venv/bin/activate

# Run chunking pipeline
python -m clause.ingestion.pipeline --mode chunk

# Output: JSONs in /data/processed/chunks/
#         Relationships in /data/processed/graph/relations.csv
```

### Phase 2: Start Docker Services

```bash
# Build and start containers
docker-compose up -d

# Verify services are running
docker ps
```

### Phase 3: Build Knowledge Graph

```bash
python -m clause.graph.builder --load-from /data/processed/graph/relations.csv
```

### Phase 4: Index Embeddings

```bash
python -m clause.indexing.vector_store --load-chunks /data/processed/chunks/
```

### Phase 5: Test Retrieval

```bash
# Start interactive shell
python -m clause.retrieval.test_retrieval

> query: What are compliance requirements for a private limited company?
> Retrieved: [chunk_id: section_42_subsection_1, score: 0.89, ...]
```

---

## Next Steps

- [ ] Code chunking pipeline (parsers + chunker + metadata)
- [ ] Test on sample PDF
- [ ] Start Docker services
- [ ] Build Neo4j schema
- [ ] Implement vector indexing
- [ ] Build hybrid retrieval
- [ ] Implement agentic loop
- [ ] LLM generation + citations
- [ ] Evaluation suite
- [ ] API routes
- [ ] Streamlit frontend

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| Orchestration | LangGraph | 0.0.19+ |
| LLM | Claude Sonnet | Latest |
| Embeddings | text-embedding-3-large | OpenAI |
| Vector DB | Qdrant | Latest |
| Graph DB | Neo4j | Latest |
| Sparse Search | BM25s | 0.2.2+ |
| Reranker | Cohere Rerank v3 | API |
| Parsing | unstructured, pdfplumber, camelot | Latest |
| Framework | FastAPI | 0.104+ |

---

## Contributing

This is a personal/team project. Follow the architecture in `context.md` before making changes.

---

## License

[Your License Here]

---

**Questions?** Refer to `context.md` for architectural decisions and `README.md` for setup.
