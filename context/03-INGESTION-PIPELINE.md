# 03 — Ingestion Pipeline

Covers Steps 1-3: Document Parsing, Hierarchical Chunking, and Contextual Enrichment.

---

## Step 1 — Document Parsing

**Files**: `clause/ingestion/parsers/pdf_parser.py` | `clause/ingestion/parsers/html_parser.py` | `clause/ingestion/parsers/table_extractor.py`

### PDF Parser

```python
# clause/ingestion/parsers/pdf_parser.py

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Title, NarrativeText, Table, ListItem
import pdfplumber

def parse_pdf(filepath: str) -> str:
    """
    Parse a legal PDF into clean text preserving section structure.
    
    Strategy:
    1. Use unstructured to detect document structure (titles, narrative, tables)
    2. Preserve Title elements as section markers with newline padding
    3. Extract tables separately via table_extractor
    4. Return clean text with section boundaries intact
    """
    elements = partition_pdf(
        filename=filepath,
        strategy="hi_res",           # Better accuracy for legal docs
        infer_table_structure=True,   # Detect tables
        include_page_breaks=False
    )
    
    text_parts = []
    for el in elements:
        if isinstance(el, Title):
            # Add extra newline before titles so section splitter regex fires
            text_parts.append(f"\n\n{el.text}\n")
        elif isinstance(el, (NarrativeText, ListItem)):
            text_parts.append(el.text)
        elif isinstance(el, Table):
            # Preserve table as pipe-delimited for table_extractor to detect
            text_parts.append(el.text)
    
    return "\n".join(text_parts)
```

### HTML Parser

```python
# clause/ingestion/parsers/html_parser.py

from bs4 import BeautifulSoup

def parse_html(filepath: str) -> str:
    """
    Parse India Code HTML into clean text.
    India Code wraps sections in <div class="section"> or similar.
    Preserve section numbers exactly as they appear.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    # Remove nav, header, footer — legal content only
    for tag in soup(["nav", "header", "footer", "script", "style"]):
        tag.decompose()
    
    return soup.get_text(separator="\n", strip=True)
```

### Table Extractor

```python
# clause/ingestion/parsers/table_extractor.py

import camelot

def extract_tables(filepath: str) -> list[dict]:
    """
    Extract structured tables from PDFs (penalty schedules, fee tables).
    Returns list of dicts with page, dataframe, and raw text.
    
    Why camelot: pdfplumber.extract_table() misses many legal tables.
    camelot's lattice mode handles bordered tables reliably.
    """
    tables = camelot.read_pdf(filepath, pages="all", flavor="lattice")
    result = []
    for table in tables:
        result.append({
            "page": table.page,
            "df": table.df,
            "raw": table.df.to_string(),
            "structured": table.df.to_dict(orient="records")
        })
    return result
```

---

## Step 2 — Hierarchical Chunking

**Files**: `clause/ingestion/chunkers/section_chunker.py` | `clause/ingestion/chunkers/hierarchical_chunker.py`

### Data Model

```python
# clause/ingestion/chunkers/section_chunker.py

from pydantic import BaseModel
from typing import Optional

class LegalChunk(BaseModel):
    chunk_id: str                          # Deterministic. Format: ACT_S{n} or ACT_S{n}_{m}
    type: str                              # "document" | "parent" | "child" | "table"
    parent_id: Optional[str] = None        # Only on child chunks
    act: str                               # e.g. "Companies Act 2013"
    chapter: Optional[str] = None
    section_number: Optional[str] = None   # e.g. "42", "42(3)", "Rule 14"
    section_title: Optional[str] = None
    text: str                              # Original text — shown in citations
    contextualized_text: Optional[str] = None  # Set by contextualizer — used for embedding
    cross_references: list[str] = []       # ["Section 43", "Rule 14"] — become graph edges
    tokens: int
    source_file: str
    sentence_window: Optional[str] = None  # ±2 sentences around child chunk
```

### Splitting Logic — Priority Order

```python
# Regex separators in priority order — never change this order
LEGAL_SEPARATORS = [
    r'\n(?=Section\s+\d+[A-Z]?\b)',     # "Section 42" — primary boundary
    r'\n(?=\d+[A-Z]?\.\s)',             # "42. Short title" — numbered sections
    r'\n(?=\(\d+\)\s)',                 # "(1) Every company shall..." — sub-sections
    r'\n(?=\([a-z]\)\s)',               # "(a) the company..." — clauses
    r'\n(?=Provided\s+that)',           # Proviso start — flag, do not split here
    r'(?<=\.)\s{2,}(?=[A-Z])',          # Sentence boundary fallback
]
```

### Critical Legal Rules — Enforced in Code

```python
# Rule 1: Proviso merging
# "Provided that..." has no standalone meaning. Must merge with preceding chunk.
# Detection: chunk.text.strip().startswith("Provided that") or "Provided further that"

# Rule 2: Explanation merging  
# "Explanation — For the purposes of this section..."
# Has no standalone meaning. Must merge with parent section.
# Detection: chunk.text.strip().startswith("Explanation")

# Rule 3: Cross-reference detection
# Patterns to detect and store in cross_references list:
CROSS_REF_PATTERNS = [
    r'[Ss]ection\s+\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\))?',   # "Section 42(3)(a)"
    r'[Ss]ub-?[Ss]ection\s+\(\d+\)',                          # "sub-section (3)"
    r'[Rr]ule\s+\d+[A-Z]?',                                   # "Rule 14A"
    r'[Ss]chedule\s+[IVXLC]+',                                # "Schedule IV"
    r'[Ff]orm\s+[A-Z]+-\d+[A-Z]?',                           # "Form MGT-7"
    r'[Cc]lause\s+\(\d+\)',                                    # "clause (3)"
]

# Rule 4: Table chunks — never split
# Detect by presence of | characters or camelot extraction flag
# Chunk whole table as type="table", structured=list[dict]

# Rule 5: Token bounds — enforce and warn
# child: 128–256 tokens. Log WARNING if outside bounds, never silently truncate.
# parent: 512–1024 tokens. If section exceeds 1024, split at sub-section boundary only.
```

### Chunk ID Format — Must Be Deterministic

```python
# Document chunk:  CA2013          (act abbreviation)
# Parent chunk:    CA2013_S42      (act + section number)
# Child chunk:     CA2013_S42_3    (act + section + sub-section index)
# Table chunk:     CA2013_S42_T1   (act + section + table index)

# Act abbreviations (locked):
ACT_ABBREVIATIONS = {
    "Companies Act 2013": "CA2013",
    "Companies (Incorporation) Rules 2014": "CIR2014",
    "Companies (Share Capital) Rules 2014": "CSCR2014",
    "Companies (Accounts) Rules 2014": "CAR2014",
    "Companies (Meetings) Rules 2014": "CMR2014",
    "Companies (Directors) Rules 2014": "CDR2014",
    "SEBI (ICDR) Regulations 2018": "ICDR2018",
    "SEBI (AIF) Regulations 2012": "AIF2012",
    "DPIIT Startup Recognition Guidelines": "DPIIT_SRG",
}
```

---

## Step 3 — Contextual Enrichment

**File**: `clause/ingestion/enrichment/contextualizer.py`

```python
# clause/ingestion/enrichment/contextualizer.py

import asyncio
import anthropic
from clause.ingestion.chunkers.section_chunker import LegalChunk

CONTEXTUALIZATION_PROMPT = """You are processing a legal document for a RAG retrieval system.

Here is the full parent section from {act_name}:
<parent_section>
{parent_text}
</parent_section>

Here is a specific sub-section chunk extracted from it:
<chunk>
{chunk_text}
</chunk>

Write exactly 1-2 sentences that:
1. Identify which act and section number this chunk belongs to
2. Describe the specific legal concept or obligation this chunk addresses
3. Note any key conditions, entity types, or thresholds mentioned

Be precise. Use the exact section number and act name.
Return only the 1-2 sentences, no preamble, no explanation.

Example output format:
"This sub-section is from Section 42(3) of the Companies Act 2013, governing the 60-day cooling period between private placements. It specifies the restriction on issuing fresh offers within this period."
"""

async def contextualize_chunk(
    child: LegalChunk,
    parent: LegalChunk,
    client: anthropic.AsyncAnthropic,
    model: str = "claude-haiku-20240307"
) -> LegalChunk:
    """
    Generate context sentence for a child chunk using its parent section.
    Uses Haiku for cost efficiency — this task does not need Sonnet quality.
    """
    response = await client.messages.create(
        model=model,
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": CONTEXTUALIZATION_PROMPT.format(
                act_name=child.act,
                parent_text=parent.text,
                chunk_text=child.text
            )
        }]
    )
    
    context_sentence = response.content[0].text.strip()
    child.contextualized_text = f"{context_sentence}\n\n{child.text}"
    return child

async def contextualize_all(
    children: list[LegalChunk],
    parent_map: dict[str, LegalChunk],  # parent_id → parent chunk
    concurrency: int = 10               # max parallel Haiku calls
) -> list[LegalChunk]:
    """
    Contextualize all child chunks with controlled concurrency.
    concurrency=10 is safe for Haiku rate limits.
    """
    semaphore = asyncio.Semaphore(concurrency)
    client = anthropic.AsyncAnthropic()
    
    async def bounded_contextualize(child: LegalChunk) -> LegalChunk:
        async with semaphore:
            parent = parent_map.get(child.parent_id)
            if not parent:
                # Fallback: use chunk text as-is (no parent found)
                child.contextualized_text = child.text
                return child
            return await contextualize_chunk(child, parent, client)
    
    tasks = [bounded_contextualize(child) for child in children]
    return await asyncio.gather(*tasks)
```


---

## Pipeline Orchestration

**File**: `clause/ingestion/pipeline.py`

All three steps (parsing, chunking, enrichment) are orchestrated in a single pipeline:

```python
# clause/ingestion/pipeline.py

async def run_ingestion_pipeline(source_dir: str):
    """
    Full pipeline: Parse → Chunk → Enrich → Index
    Called by CLI (scripts/run_ingestion.py) or API (POST /ingest).
    """
    # Step 1: Parse all PDFs and HTMLs
    parsed_docs = parse_all_documents(source_dir)
    
    # Step 2: Create chunks with hierarchy
    chunks = create_hierarchical_chunks(parsed_docs)
    
    # Step 3: Enrich chunks with context
    enriched = await contextualize_all(chunks)
    
    # Step 4-6: Index into Qdrant, BM25, Neo4j
    # (See 04-INDEXING.md)
    await index_all(enriched)
    
    return {
        "chunks_created": len(enriched),
        "nodes_created": graph_stats["nodes"],
        "edges_created": graph_stats["edges"],
    }
```

---

## 🔗 Next Steps

- Indexing steps: [04-INDEXING.md](04-INDEXING.md)
- Query pipeline: [05-RETRIEVAL-PIPELINE.md](05-RETRIEVAL-PIPELINE.md)
