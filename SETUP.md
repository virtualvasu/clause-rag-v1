# Clause Pipeline Setup Guide

This guide walks you through setting up and running the **Clause Ingestion Pipeline** that chunks your PDFs into the hierarchical structure.

---

## Prerequisites

### System Dependencies

Before running the pipeline, install system packages required for PDF processing:

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install -y \
  poppler-utils \
  tesseract-ocr \
  ghostscript

# On macOS
brew install poppler tesseract ghostscript
```

**Why these?**
- `poppler-utils` - PDF text extraction and rendering
- `tesseract-ocr` - Optical character recognition for scanned PDFs
- `ghostscript` - PostScript/PDF processing (dependency)

### Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

---

## Installation

### Install Dependencies

```bash
pip install -r requirements.txt
```

**Key packages installed:**
- `pdfplumber` - Advanced PDF text extraction preserving layout
- `unstructured` - Document structure detection
- `camelot-py` - Table extraction from PDFs
- Other ingestion/indexing/LLM dependencies

**Note:** First install can take 5-10 minutes due to package compilation.

---

## Running the Pipeline

### Option 1: Quick Start (Recommended)

```bash
python run_pipeline.py
```

This will:
1. ✅ Find all PDFs in `data/raw/`
2. ✅ Parse each PDF (extract text + tables + structure)
3. ✅ Chunk hierarchically (Section → Subsection → Clause)
4. ✅ Extract special elements (definitions, penalties, cross-refs)
5. ✅ Save outputs to `data/processed/`
6. ✅ Generate summary report

### Option 2: Manual Execution

```bash
# Activate environment
source venv/bin/activate

# Run pipeline directly
python -m clause.ingestion.pipeline

# Or with specific documents only
python -c "
from clause.ingestion.pipeline import IngestionPipeline
p = IngestionPipeline()
p.run(documents=['Companies_Act_2013', 'SEBI_ICDR_Regulations_2018'])
"
```

---

## Pipeline Execution

### Expected Output

```
============================================================
CLAUSE INGESTION PIPELINE STARTING
============================================================

============================================================
Processing: Companies_Act_2013
File: data/raw/companies_act/Companies_Act_2013.pdf
============================================================
Step 1: Parsing PDF...
  ✓ Extracted text (2.4M chars)
Step 2: Chunking hierarchically...
  ✓ Created 420 chunks
Step 3: Extracting special elements...
  ✓ Extracted 145 special elements
Step 4: Saving chunks...
  ✓ Saved 420 chunks to data/processed/chunks
Step 5: Saving special elements...
  ✓ Saved 145 special elements
✅ Completed: Companies_Act_2013

... (processing other documents) ...

============================================================
PIPELINE SUMMARY
============================================================
✅ Successful: 10/10
❌ Failed: 0
📊 Total Chunks: 4,250
🔍 Total Special Elements: 1,180
📁 Output Directory: data/processed/
============================================================
```

**Processing time:** ~10-20 minutes for all 10 Phase 1 documents (depends on system)

---

## Pipeline Outputs

### Directory Structure

```
data/processed/
├── chunks/                          # Individual chunk JSON files
│   ├── section_1_full.json          # Full section (Level 1)
│   ├── section_1_subsection_1.json  # Subsection (Level 2)
│   ├── section_1_subsection_1_clause_a.json  # Clause (Level 3)
│   └── ... (1000s of chunk files)
│
├── entities/                        # Extracted entities & metadata
│   ├── all_chunks_metadata.json     # Consolidated chunk metadata
│   ├── all_definitions.json         # All definitions
│   ├── all_penalties.json           # All penalties
│   ├── all_thresholds.json          # All thresholds
│   ├── all_cross_references.json    # All cross-refs
│   ├── all_exceptions.json          # All exceptions
│   ├── Companies_Act_2013_definitions.json
│   ├── Companies_Act_2013_penalties.json
│   └── SUMMARY.md                   # Summary report
│
└── graph/                           # Graph relationships
    ├── relationships.csv            # CSV for Neo4j import
    └── entities_with_types.json     # Entity types
```

### Chunk File Format

Example chunk JSON:

```json
{
  "chunk_id": "section_42_subsection_1",
  "text": "Section 42(1): Every company shall have at least one director...",
  "level": "subsection",
  "document": "Companies_Act_2013",
  "act_name": "Companies Act 2013",
  "section": "42",
  "subsection": "1",
  "heading": "Appointment of directors",
  "parent_chunk_id": "section_42_full",
  "children_ids": [],
  "token_count": 87,
  "full_path": "Companies Act 2013 > Section 42 > Subsection (1)",
  "type": "standard",
  "applies_to": ["PrivateLimited", "PublicCompany"],
  "condition_tags": ["director_requirement"],
  "cross_references": ["Section 2(34)", "Rule 4"],
  "effective_date": "2013-09-12"
}
```

### Metadata File Format

Consolidated metadata (all_chunks_metadata.json):

```json
[
  {
    "chunk_id": "section_1_full",
    "level": "section",
    "section": "1",
    "document": "Companies_Act_2013",
    "token_count": 450,
    "children_ids": [
      "section_1_subsection_1",
      "section_1_subsection_2"
    ]
  },
  ...
]
```

---

## Troubleshooting

### Issue: "pdfplumber not found"

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "tesseract-ocr not installed"

**Solution:** Install system package:
```bash
sudo apt install tesseract-ocr  # Ubuntu/Debian
brew install tesseract           # macOS
```

### Issue: "No such file or directory: data/raw/"

**Solution:** Ensure PDFs are in correct location:
```bash
ls -la data/raw/
# Should show subdirectories: companies_act/, sebi/, etc.
```

### Issue: Pipeline is slow (taking >30 minutes)

**Possible causes:**
- Large PDFs with tables (camelot is slower)
- OCR being performed on scanned PDFs
- Limited system RAM or disk I/O

**Solution:** 
- Run on a machine with 8GB+ RAM
- Process documents one at a time
- Use `p.run(documents=['Companies_Act_2013'])` to test

### Issue: "ImportError: No module named 'unstructured'"

**Solution:**
```bash
pip install unstructured python-magic-mime

# For extra document format support
pip install unstructured[pdf,table-structure]
```

---

## Next Steps After Pipeline

Once chunks are created, you have 3 options:

### Option 1: Vector Indexing (Qdrant)
```bash
# (After Docker containers are running)
python -m clause.indexing.vector_store --load-chunks data/processed/chunks/
```

### Option 2: Graph Loading (Neo4j)
```bash
# (After Docker containers are running)
python -m clause.graph.builder --load-from data/processed/graph/relationships.csv
```

### Option 3: BM25 Indexing
```bash
python -m clause.indexing.bm25_index --load-chunks data/processed/chunks/
```

---

## Performance Tips

### Parallel Processing (Future Enhancement)
Currently processes documents sequentially. For future optimization:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = executor.map(pipeline._process_document, documents)
```

### Caching
Parsed PDFs are cached automatically. To force reparse:
```bash
rm -rf data/processed/
python run_pipeline.py
```

---

## Verification

After pipeline completes, verify outputs:

```bash
# Check chunk count
find data/processed/chunks -type f -name "*.json" | wc -l

# View sample chunk
cat data/processed/chunks/section_1_full.json | head -20

# Check metadata size
du -sh data/processed/entities/

# Read summary
cat data/processed/entities/SUMMARY.md
```

---

## Questions?

Refer to:
- **README.md** - Project overview & architecture
- **context.md** - Decision rationale
- **Chunking Strategy** (in README.md) - How chunks are created
