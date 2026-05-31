# 🎯 Clause Pipeline - READY TO RUN

## What Was Just Created

### ✅ Chunking Pipeline (7 Python modules)

```
clause/ingestion/
├── __init__.py
├── pipeline.py                          ← Main orchestrator
├── parsers/
│   ├── __init__.py
│   └── pdf_parser.py                    ← PDF extraction (pdfplumber + unstructured)
└── chunkers/
    ├── __init__.py
    ├── hierarchical_chunker.py          ← 3-level hierarchical chunking
    └── special_elements.py              ← Extract definitions, penalties, cross-refs
```

**Pipeline Flow:**
```
PDF Files (data/raw/) 
    ↓
[PDFParser] → Extract text, tables, structure
    ↓
[HierarchicalChunker] → Split into Level 1/2/3 chunks
    ↓
[SpecialElementsExtractor] → Find definitions, penalties, cross-references
    ↓
[Save Outputs] → JSONs to data/processed/chunks/, entities/, graph/
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y poppler-utils tesseract-ocr ghostscript

# macOS
brew install poppler tesseract ghostscript
```

### Step 2: Install Python Dependencies

```bash
# Create venv
python3.11 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install
pip install -r requirements.txt
```

### Step 3: Run Pipeline

```bash
# Test first (runs on first PDF only)
python test_pipeline.py

# Then run full pipeline
python run_pipeline.py
```

**That's it!** ✨

---

## 📊 What The Pipeline Creates

### Output: /data/processed/

```
chunks/                  ← 1000s of JSON chunk files
├── section_1_full.json                  (Level 1: Full section)
├── section_1_subsection_1.json          (Level 2: Subsection)
├── section_1_subsection_1_clause_a.json (Level 3: Clause)
└── ...

entities/               ← Consolidated metadata & special elements
├── all_chunks_metadata.json             (All chunk records)
├── all_definitions.json                 (Extracted definitions)
├── all_penalties.json                   (Extracted penalties)
├── all_cross_references.json
├── all_thresholds.json
└── SUMMARY.md                           (Summary report)

graph/                  ← Neo4j import files
├── relationships.csv                    (Parent-child + cross-ref edges)
└── entities_with_types.json
```

---

## 📋 Chunking Strategy Implemented

### ✅ Three-Level Hierarchy

**Level 1: Full Section (Parent)**
- Size: 1-5 KB (~300-1500 tokens)
- Example: Entire "Section 42: Appointment of directors"
- Purpose: Full legal context

**Level 2: Subsection (Child)**
- Size: 200-500 tokens
- Example: "Section 42(1): Every company shall have..."
- Purpose: Vector search retrieval

**Level 3: Clause (Granular)**
- Size: 50-200 tokens
- Example: "Section 42(1)(a): at least one director shall be resident..."
- Purpose: Precise citations

### ✅ Special Elements Extracted

- ✓ **Definitions** — "director" means... (Section 2(34))
- ✓ **Penalties** — Punishable with fine ₹1L-₹5L or imprisonment
- ✓ **Thresholds** — Turnover < 50 crores, shareholding > 25%
- ✓ **Cross-References** — "See Section 42", "As per Rule 4"
- ✓ **Exceptions** — "Provided that...", "Notwithstanding..."

### ✅ Rich Metadata

Each chunk includes:
- Hierarchical path: "Companies Act 2013 > Part I > Section 42 > Subsection (1)"
- Parent-child relationships (for graph)
- Entity type tags: PrivateLimited, PublicCompany, etc.
- Condition tags: turnover, foreign_directors, etc.
- Cross-reference links: Section 42 → Section 2(34)
- Effective dates & amendments

---

## 📚 Documentation Created

| File | Purpose |
|------|---------|
| **README.md** | Project overview + detailed chunking strategy |
| **SETUP.md** | Step-by-step setup guide (this file explains) |
| **context.md** | Architecture decisions & tech stack |
| **run_pipeline.py** | Quick-start script |
| **test_pipeline.py** | Test on sample PDF first |

---

## ⏱️ Expected Runtime

| Step | Time |
|------|------|
| PDF Parsing | 30 sec - 2 min per document |
| Hierarchical Chunking | 20 sec - 1 min per document |
| Special Elements Extraction | 10 sec - 30 sec per document |
| **Total for 10 documents** | **~10-20 minutes** |

---

## 🔧 What Happens Next

After pipeline runs successfully:

1. **Verify chunks** → `ls -la data/processed/chunks/ | head`
2. **Check metadata** → `cat data/processed/entities/SUMMARY.md`
3. **Start Docker** → `docker-compose up -d`
4. **Index in Qdrant** → Vector embeddings
5. **Load into Neo4j** → Knowledge graph
6. **Build BM25 index** → Sparse search
7. **Test retrieval** → Hybrid search results

---

## ⚙️ Files Overview

### Core Pipeline Modules

**pdf_parser.py** (150 lines)
- `PDFParser.parse()` — Main extraction
- `extract_text_with_layout()` — Text with layout preservation
- `extract_tables()` — Table extraction
- `detect_structure()` — Section detection

**hierarchical_chunker.py** (350 lines)
- `HierarchicalChunker.chunk()` — Main orchestrator
- `_extract_sections()` — Find sections
- `_extract_subsections()` — Find (1), (2), subsections
- `_extract_clauses()` — Find (a), (b), (i), (ii) clauses
- `_create_*_chunk()` — Create Level 1/2/3 chunks

**special_elements.py** (300 lines)
- `SpecialElementsExtractor.extract_all()` — Main method
- `_extract_definitions()` — Legal definitions
- `_extract_penalties()` — Penalties & fines
- `_extract_thresholds()` — Business conditions
- `_extract_cross_references()` — Section links
- `_extract_exceptions()` — Provisos & exceptions

**pipeline.py** (450 lines)
- `IngestionPipeline.run()` — Main orchestrator
- `_process_document()` — Process single PDF
- `_save_consolidated_outputs()` — Save all results
- `_create_relationships_csv()` — For Neo4j import

### Runner Scripts

**run_pipeline.py** — Start full pipeline with verification
**test_pipeline.py** — Test on first PDF (verify setup)

---

## 🐛 Troubleshooting

### Issue: "ImportError: No module named 'unstructured'"
```bash
pip install -r requirements.txt
```

### Issue: "tesseract-ocr: command not found"
```bash
sudo apt install tesseract-ocr  # Ubuntu
brew install tesseract          # macOS
```

### Issue: "No such file or directory: data/raw/"
```bash
ls data/raw/  # Verify PDFs are here
```

### Issue: Pipeline is very slow
- Check disk space: `df -h`
- Check RAM: `free -h`
- Run single document: `p.run(['Companies_Act_2013'])`

---

## 📖 How to Use

### For Development

```bash
# Activate venv
source venv/bin/activate

# Test on sample PDF
python test_pipeline.py

# Run full pipeline
python run_pipeline.py

# Process specific documents only
python -c "
from clause.ingestion.pipeline import IngestionPipeline
p = IngestionPipeline()
p.run(['Companies_Act_2013', 'SEBI_ICDR_Regulations_2018'])
"
```

### For Production

```bash
# Run in Docker (after building)
docker build -f Dockerfile.api -t clause-api .
docker run clause-api python -m clause.ingestion.pipeline
```

---

## ✨ Key Features

✅ **Hierarchical Chunking** — 3 levels with parent-child relationships
✅ **Structure Preservation** — Maintains legal document hierarchy
✅ **Special Elements** — Definitions, penalties, conditions extracted
✅ **Metadata Rich** — Every chunk tagged with context
✅ **Cross-References** — Edges created for graph traversal
✅ **Production Ready** — Error handling, logging, resumable
✅ **Well Documented** — Code comments + setup guides
✅ **Extensible** — Easy to add new parsers/chunkers

---

## 🎓 Learning Resources

- **How hierarchical chunking works?** → See README.md "Chunking Strategy"
- **Why this architecture?** → See context.md "Architecture"
- **How to extend?** → Add new parsers in clause/ingestion/parsers/
- **How to debug?** → Enable DEBUG logging: `logging.getLogger().setLevel(logging.DEBUG)`

---

## 🚀 Next Big Steps

After pipeline successfully completes:

1. **Vector Indexing** (Phase 3) — Embed chunks in Qdrant
2. **Graph Loading** (Phase 4) — Import relationships to Neo4j
3. **Sparse Search** (Phase 5) — Build BM25 index
4. **Hybrid Retrieval** (Phase 6) — Combine vector + sparse + graph
5. **Agentic Loop** (Phase 7) — LangGraph reasoning
6. **LLM Generation** (Phase 8) — Claude Sonnet with citations
7. **Evaluation** (Phase 9) — RAGAS metrics
8. **API Routes** (Phase 10) — REST endpoints

---

## 📞 Questions?

Refer to:
- **README.md** → Project overview & chunking deep-dive
- **SETUP.md** → Detailed setup instructions
- **context.md** → Architecture decisions
- Code comments → Detailed explanations in each module

---

## ✅ You're Ready!

```bash
# Next command:
python run_pipeline.py
```

That's all you need to transform your PDFs into a structured, queryable corpus! 🎉

Happy chunking! 🚀
