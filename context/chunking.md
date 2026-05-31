Read CONTEXT.md fully before writing any code.

## Task: Build the Chunking Pipeline for Clause

Implement the complete chunking strategy for the Clause project — a GraphRAG system over Indian corporate and startup law documents (Companies Act 2013, SEBI regulations, MCA Rules etc).

---

## Chunking Architecture to Implement

Three-layer hierarchical chunking with these exact layers:

**Layer 1 — Document Metadata**
Not used for retrieval. Captures document-level metadata for Neo4j graph nodes.
Fields: chunk_id, type="document", name, year, ministry, source_url, total_sections

**Layer 2 — Parent Chunk (Section-level)**
512–1024 tokens. Sent to LLM as generation context (never directly retrieved).
One parent = one complete legal section with all its sub-sections intact.
Fields: chunk_id (format: ACT_S{n} e.g. CA2013_S42), type="parent", act, chapter, section_number, section_title, text, cross_references (list of detected references), tokens, source_file

**Layer 3 — Child Chunk (Sub-section level)**
128–256 tokens. These are what get embedded and searched via vector + BM25.
One child = one sub-section or logical clause.
Fields: chunk_id (format: ACT_S{n}_{m} e.g. CA2013_S42_3), type="child", parent_id, act, section_number, text, tokens, source_file

**Additionally — Sentence Window**
For each child chunk, store a sentence_window field containing ±2 sentences of surrounding context. This is used at generation time to avoid cut-off context, not at retrieval time.

**Additionally — Table Chunks**
Detected tables (fee schedules, penalty tables) are extracted whole as single chunks.
Fields: chunk_id, type="table", parent_id, act, section_number, raw_text, structured (list of dicts parsed from table), source_file

---

## Splitting Logic — Priority Order

Do NOT use LangChain RecursiveCharacterTextSplitter as the primary splitter. Build a custom regex-based legal section splitter first. Fall back to recursive token splitting only if a section exceeds 1024 tokens.

Separator priority order:
1. `\n(?=Section \d+)` — Section boundaries (highest priority)
2. `\n(?=\(\d+\))` — Sub-section boundaries
3. `\n(?=\([a-z]\))` — Clause boundaries
4. Sentence boundary — fallback only

---

## Critical Legal Structure Rules

These are non-negotiable and must be enforced in code with comments explaining why:

1. **Provisos must never be separated from their parent clause.**
   Detect with: text starting with "Provided that" or "Provided further that"
   Action: Always merge proviso with the immediately preceding sub-section/clause chunk

2. **Explanations must never be separated from their parent section.**
   Detect with: text starting with "Explanation —" or "Explanation.—"
   Action: Always merge explanation with parent section chunk

3. **Cross-references must be detected and stored.**
   Detect patterns like: "section 2(68)", "sub-section (3) of section 42", "Rule 14", "Schedule IV"
   Action: Store in cross_references list on the chunk — these become graph edges later

4. **Tables must be extracted whole, never split.**
   Detect with: presence of | characters or structured tabular patterns
   Action: Extract as type="table" chunk, attempt structured parsing into list of dicts

---

## File to Create

`clause/ingestion/chunkers/section_chunker.py`

The file must contain:

1. `LegalChunk` — Pydantic model representing a single chunk with all fields above
2. `SectionChunker` — main class with:
   - `chunk_document(text: str, metadata: dict) -> List[LegalChunk]` — full pipeline
   - `_split_into_sections(text: str) -> List[str]` — regex-based section splitter
   - `_create_parent_chunk(section_text: str, metadata: dict) -> LegalChunk`
   - `_create_child_chunks(parent: LegalChunk) -> List[LegalChunk]`
   - `_attach_sentence_windows(children: List[LegalChunk], full_text: str) -> List[LegalChunk]`
   - `_extract_tables(text: str, metadata: dict) -> List[LegalChunk]`
   - `_detect_cross_references(text: str) -> List[str]`
   - `_enforce_proviso_merging(chunks: List[LegalChunk]) -> List[LegalChunk]`
   - `_enforce_explanation_merging(chunks: List[LegalChunk]) -> List[LegalChunk]`
   - `_count_tokens(text: str) -> int` — use tiktoken cl100k_base
3. `chunk_document(filepath: str, doc_metadata: dict) -> List[LegalChunk]` — convenience function

Also create `tests/test_chunkers.py` with tests covering:
- Proviso merging (proviso never standalone)
- Explanation merging (explanation never standalone)  
- Cross-reference detection (finds "section 42(3)", "Rule 14" etc)
- Parent-child relationship (every child has valid parent_id)
- Token bounds (children between 128–256 tokens, parents between 512–1024)
- Table extraction (table chunks have structured field populated)
- Section boundary detection (splits at correct section breaks)

---

## Code Quality Requirements

- Full type hints throughout
- Docstring on every method explaining what it does AND why (the legal reasoning)
- Inline comments on all regex patterns explaining what legal structure they match
- Raise descriptive ValueError for malformed input
- Log warnings (using Python logging) when fallback splitter is triggered
- All chunk_ids must be deterministic (same input always produces same IDs)

---

## Do Not

- Do not use LangChain text splitters as the primary splitting mechanism
- Do not split provisos from their parent clause under any circumstance
- Do not split explanations from their parent section under any circumstance
- Do not produce child chunks outside the 128–256 token range without a logged warning
- Do not hardcode act names — read them from the metadata dict passed in