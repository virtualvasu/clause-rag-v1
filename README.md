# Clause — Hybrid GraphRAG for Indian Startup Law

**Legal clarity for Indian startups** — An enterprise-grade RAG system combining vector search, sparse search, knowledge graphs, and agentic reasoning.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Chunking Strategy](#chunking-strategy)
4. [Setup & Installation](#setup--installation)
5. [Project Structure](#project-structure)
6. [Running the Pipeline](#running-the-pipeline)
7. [Next Steps](#next-steps)

---

## Project Overview

### Problem

Indian startup founders and lawyers need answers to complex, multi-hop legal questions:

- *"What are compliance requirements for a private limited company with 3 foreign directors in its first year?"*
- *"What changed for ESOP taxation between 2020 and 2023?"*
- *"Which SEBI regulations apply to a startup raising a Series B from a US VC?"*

**Baseline RAG fails** because these queries require:
- ✗ Traversing relationships across multiple acts and sections
- ✗ Conditional logic (IF entity_type == small_company AND turnover < 50Cr THEN...)
- ✗ Temporal reasoning (amendment histories, effective dates)
- ✗ Cross-document linking (SEBI regulation → Companies Act section)

### Solution

**Hybrid GraphRAG** combines:
- 🔍 **Vector Search** (dense embeddings via Qdrant)
- 🔤 **Sparse Search** (keyword matching via BM25)
- 🔗 **Knowledge Graph** (relationships via Neo4j)
- 🤖 **Agentic Loop** (reasoning via LangGraph)
- 💬 **LLM Generation** (Claude Sonnet)

---

## Architecture

```
User Query
    │
    ▼
┌──────────────────────────┐
│   Query Processor        │
│ • Query classification   │
│ • HyDE expansion         │
│ • Query normalization    │
└────────────┬─────────────┘
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
              │
              ▼
     ┌─────────────────┐
     │  RRF Fusion +   │
     │   Reranking     │
     │ (Cohere v3)     │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Knowledge Graph│
     │  Traversal      │
     │  (Neo4j)        │
     │ • Entity lookup │
     │ • Path reasoning│
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Agentic Loop   │
     │  (LangGraph)    │
     │ • CRAG check    │
     │ • Adaptive      │
     │   routing       │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │ LLM Generation  │
     │ (Claude Sonnet) │
     │ + Citations     │
     └─────────────────┘
```

---

## Chunking Strategy

### Why Hierarchical Chunking?

Legal documents have natural hierarchical structure that flat chunking destroys:

```
Companies Act 2013
  └─ Part I (Preliminary)
      └─ Chapter II (Incorporation)
          └─ Section 5 (Classification of companies)
              └─ Subsection (a), (b), (c)
                  └─ Clause (i), (ii), (iii)
                      └─ Explanation / Proviso
```

**Problems with flat chunking:**
- ❌ Chunk at subsection level → lose full section context
- ❌ Chunk at section level → lose granular detail
- ❌ Fixed-size chunks → split meaningful legal phrases

**Hierarchical solution:** Create multi-level chunks with parent-child relationships.

---

### Chunking Levels

#### **Level 1: Full Section (Parent Chunk)**

**Definition:** Entire section from heading to all subsections/provisos/explanations

**Size:** 1-5 KB (~300-1500 tokens)

**Use case:** Complex queries needing full legal context

**Example:**
```
Section 42: Appointment of directors

(1) Every company shall have at least one director and a maximum of fifteen directors...

(2) Provided that a private company or an unlisted public company may...

(3) The central government may...

Explanation: For the purposes of this section...
```

**Metadata:**
```json
{
  "chunk_id": "section_42_full",
  "level": "section",
  "section": "42",
  "heading": "Appointment of directors",
  "token_count": 450,
  "has_subsections": true,
  "has_provisos": true,
  "children": [
    "section_42_subsection_1",
    "section_42_subsection_2",
    "section_42_subsection_3"
  ]
}
```

---

#### **Level 2: Subsection/Proviso (Child Chunk)**

**Definition:** Individual subsection (1), (2), (3) or proviso or explanation

**Size:** 200-500 tokens (~60-150 words)

**Use case:** Precise targeted retrieval for vector search

**Example:**
```
Section 42(2): Provided that a private company or an unlisted public company 
may have such number of directors as may be prescribed.
```

**Metadata:**
```json
{
  "chunk_id": "section_42_subsection_2",
  "level": "subsection",
  "section": "42",
  "subsection": "2",
  "type": "proviso",
  "parent_chunk_id": "section_42_full",
  "token_count": 95,
  "applies_to": ["PrivateLimited", "UnlistedPublic"]
}
```

---

#### **Level 3: Clause/Definition (Granular Chunk)**

**Definition:** Individual clause (a), (b), (c), (i), (ii) or single extracted definition

**Size:** 50-200 tokens (~15-60 words)

**Use case:** Specific obligations, precise citations

**Example:**
```
Section 42(1)(a): at least one director shall be resident in India 
for a period of not less than one hundred and eighty-three days 
during the relevant financial year
```

**Metadata:**
```json
{
  "chunk_id": "section_42_subsection_1_clause_a",
  "level": "clause",
  "section": "42",
  "subsection": "1",
  "clause": "a",
  "parent_chunk_id": "section_42_subsection_1",
  "token_count": 42,
  "entity_type": "residency_requirement",
  "condition": "resident_in_india",
  "duration_days": 183
}
```

---

### Special Document Elements

#### **1. Definitions**

**Strategy:** Extract and create separate chunks

**Example:**
```
"Director" defined in Section 2(34):

"director" means a person who is appointed to act as director of a company.

Applies in: All sections of the Act
Cross-references: Section 42, 149, 160, 165...
```

**Metadata:**
```json
{
  "chunk_id": "definition_director",
  "type": "definition",
  "defined_term": "director",
  "defined_in_section": "2(34)",
  "definition_text": "...",
  "used_in_sections": [42, 149, 160, 165],
  "cross_references": ["Section 2(34)", "Section 42", ...]
}
```

---

#### **2. Penalties & Conditions**

**Strategy:** Extract as atomic chunks, create structured relationships

**Example from Companies Act:**
```
Section 149(7): Contravention of subsection (1) shall be punishable 
with fine which shall not be less than ₹1 lakh but which may extend 
to ₹5 lakh, and in case of a company with turnover exceeding ₹100 crore, 
the fine shall not be less than ₹2 lakh but may extend to ₹10 lakh.
```

**Metadata:**
```json
{
  "chunk_id": "penalty_section_149_7",
  "type": "penalty",
  "section": "149",
  "offense": "contravention_of_section_149_subsection_1",
  "penalty_min_inr": 100000,
  "penalty_max_inr": 500000,
  "conditional_penalty": {
    "condition": "turnover > 100 crore",
    "penalty_min_inr": 200000,
    "penalty_max_inr": 1000000
  },
  "applies_to": ["PublicCompany", "PrivateLimited"]
}
```

---

#### **3. Tables (Schedules, Fees, Forms)**

**Strategy:** Treat as atomic (don't split), extract row relationships

**Example:**
```
Schedule VIII: Filing Fees

Company Type | MCA Registrar | Registrar Office | Total
Private Ltd  | ₹1,000        | ₹500              | ₹1,500
Public Ltd   | ₹5,000        | ₹2,000            | ₹7,000
```

**Processing:**
- Don't split table rows
- Extract each row as a separate chunk
- Create relationships: CompanyType → Fee

**Metadata:**
```json
{
  "chunk_id": "schedule_8_row_1",
  "type": "table_row",
  "source": "Schedule VIII",
  "title": "Filing Fees",
  "company_type": "PrivateLimited",
  "mca_registrar_fee": 1000,
  "registrar_office_fee": 500,
  "total_fee": 1500,
  "currency": "INR"
}
```

---

#### **4. Cross-References**

**Strategy:** Parse and create Neo4j edges for graph traversal

**Examples found in documents:**
- "See Section X of the Companies Act"
- "As per Rule Y, clause (a)"
- "In accordance with Schedule Z"
- "Amended by Amendment Act YYYY"

**Parsing & Storage:**
```json
{
  "chunk_id": "section_42_cross_ref_1",
  "type": "cross_reference",
  "from_section": "42",
  "references": [
    {
      "target": "section_2_34",
      "reference_text": "definition of director",
      "reference_type": "definition"
    },
    {
      "target": "rule_4_incorporation_rules",
      "reference_text": "Form INC-12A",
      "reference_type": "related_form"
    }
  ]
}
```

**Graph edges created:**
- `(Section:42)-[:REFERENCES]->(Section:2_34)`
- `(Section:42)-[:REQUIRES_FORM]->(Form:INC_12A)`

---

#### **5. Amendments & Temporal Data**

**Strategy:** Store original + amendment separately with effective dates

**Example:**
```
Companies Act 2013, Section 42 (Original, 2013-09-12):
Every company shall have at least one director...

Companies (Amendment) Act 2015, Section 42 (Amended, 2015-03-02):
Every company shall have at least one director in India...
[Modified: Added "in India" requirement]

Companies (Amendment) Act 2017, Section 42 (Amended, 2017-12-10):
Every company shall have at least one director...
[Modified: Changed tenure requirement from 180 to 183 days]
```

**Metadata:**
```json
{
  "chunk_id": "section_42_history",
  "type": "amendment_history",
  "section": "42",
  "versions": [
    {
      "version_id": "section_42_v1",
      "effective_date": "2013-09-12",
      "amendment_act": "Companies Act 2013",
      "text": "...",
      "change_summary": "Original provision"
    },
    {
      "version_id": "section_42_v2",
      "effective_date": "2015-03-02",
      "amendment_act": "Companies (Amendment) Act 2015",
      "text": "...",
      "change_summary": "Added requirement: director must be in India",
      "amended_by_section": "Companies (Amendment) Act 2015, Section X"
    }
  ],
  "current_version": "section_42_v3",
  "current_effective_date": "2017-12-10"
}
```

---

### Chunking Pipeline

#### **Step 1: PDF Extraction**
- Use `pdfplumber` to extract text preserving layout
- Use `unstructured` for structure detection (headers, tables)
- Use `camelot` for table extraction with accuracy

#### **Step 2: Document Structure Detection**
- Regex patterns: "^(Section|Rule|Schedule)\s+(\d+)"
- Heading level detection
- Subsection markers: (1), (2), (a), (b), (i), (ii)

#### **Step 3: Hierarchical Splitting**
```
Full Document (Level 0)
  └─ Part/Schedule (Level 1)
      └─ Chapter (Level 2)
          └─ Section (Level 3) ← Parent chunks
              └─ Subsection/Proviso (Level 4) ← Child chunks
                  └─ Clause/Explanation (Level 5) ← Granular chunks
```

#### **Step 4: Special Element Extraction**
- Extract definitions: Look for "means", "includes", "defined as"
- Extract penalties: Look for "punishable", "fine", "imprisonment"
- Extract tables: Use camelot, verify structure
- Extract references: Look for "See Section", "Refer to", "As per"

#### **Step 5: Metadata Enrichment**
- Add hierarchical paths
- Add entity type tags (PrivateLimited, PublicCompany, etc.)
- Add condition tags (turnover, no. of shareholders, etc.)
- Count tokens using `tiktoken`
- Track amendments and effective dates

#### **Step 6: Chunk Validation**
- Verify no orphaned clauses (each clause has parent)
- Verify no truncated legal phrases
- Verify cross-references resolve
- Check token counts within ranges

#### **Step 7: Output Generation**
- Write to `/data/processed/chunks/` as JSON files
- Write relationships to `/data/processed/graph/relations.csv` for Neo4j import
- Write metadata to `/data/processed/entities/metadata.json`

---

### Chunk Size Heuristics

| Level | Min Tokens | Max Tokens | Reasoning |
|-------|-----------|-----------|-----------|
| Full Section | 300 | 1500 | Fits in LLM context, preserves full meaning |
| Subsection | 60 | 500 | Good for embedding + search balance |
| Clause | 15 | 200 | Precise retrieval, specific obligations |

**Why these ranges?**
- OpenAI's `text-embedding-3-large` ≈ 8,191 token limit
- LLM context window (Claude Sonnet): 200K tokens
- ~300 tokens ≈ 1 page of dense legal text
- BM25 effective with 50+ tokens (too small loses context)
- Qdrant embedding quality decreases below 30 tokens

---

### Expected Output Structure

```
data/
└── processed/
    ├── chunks/
    │   ├── section_42_full.json
    │   ├── section_42_subsection_1.json
    │   ├── section_42_subsection_1_clause_a.json
    │   ├── definition_director.json
    │   ├── penalty_section_149_7.json
    │   └── ... (1000+ chunk files)
    │
    ├── entities/
    │   ├── metadata.json          (all chunk metadata consolidated)
    │   ├── definitions.json       (extracted definitions)
    │   ├── penalties.json         (extracted penalties)
    │   ├── thresholds.json        (turnover, shareholder counts, etc.)
    │   └── amendments.json        (amendment history)
    │
    └── graph/
        ├── nodes.csv              (for Neo4j LOAD CSV)
        ├── relationships.csv      (for Neo4j LOAD CSV)
        └── entities_with_types.json
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- System dependencies: `poppler-utils`, `tesseract-ocr`

### Install System Dependencies

```bash
sudo apt update
sudo apt install poppler-utils tesseract-ocr -y
```

### Install Python Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Environment Setup

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

---

## Project Structure

```
clause-rag-v1/
├── README.md                          ← This file
├── context.md                         ← Project context & decisions
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
