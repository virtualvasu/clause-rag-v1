# 12 — LLM Prompts Specification

All LLM prompts as module-level constants in **`clause/generation/prompts.py`**.

> ⚠️ **Never define prompts inline in other files.** Always import from this module.

---

## Prompt Inventory

### Query Classification

**Purpose:** Determine query complexity type for routing.

**Model:** Claude Sonnet

**Prompt:**
```
Classify this legal query into exactly one category.

Query: {query}

Categories:
- SIMPLE: Single section lookup. One act, one concept, direct answer.
  Example: "What is the definition of a small company under Companies Act?"

- MULTI_HOP: Requires reasoning across multiple sections of one act.
  Example: "What are all compliance requirements in the first 90 days of incorporation?"

- CROSS_DOC: Requires information from multiple acts or regulations.
  Example: "What SEBI filings are needed when a startup issues CCPS to a foreign VC?"

- CONDITIONAL: Answer depends on conditions (entity type, thresholds, dates).
  Example: "What are the audit requirements for a startup with turnover between 2Cr and 10Cr?"

Return ONLY one word: SIMPLE, MULTI_HOP, CROSS_DOC, or CONDITIONAL
```

**Expected Output:** `MULTI_HOP`

---

### Query Expansion

**Purpose:** Generate 3 alternative phrasings to improve recall.

**Model:** Claude Sonnet

**Prompt:**
```
You are expanding a legal query to improve retrieval coverage.

Original query: {query}

Generate exactly 3 alternative phrasings of this query. Each phrasing should:
1. Use different legal terminology that might appear in the actual statute
2. Cover different angles of the same question
3. Be specific enough to retrieve relevant sections

Legal documents use formal language like "shall", "notwithstanding", "pursuant to".
Include both formal statutory language and plain English variants.

Return ONLY a JSON array of 3 strings:
["phrasing 1", "phrasing 2", "phrasing 3"]
```

**Expected Output:**
```json
[
  "What are the legal requirements for incorporation of a private company within the first 90 days?",
  "Which filings must a newly registered private company make within three months of incorporation under the Companies Act 2013?",
  "Compliance obligations for a freshly incorporated private limited company: first quarter requirements"
]
```

---

### HyDE (Hypothetical Document Embedding)

**Purpose:** Generate hypothetical statute passage for embedding + vector search.

**Model:** Claude Haiku

**Prompt:**
```
Write a short passage that would appear in an Indian legal document 
(Companies Act, SEBI regulation, or MCA rule) that directly answers this question:

Question: {query}

Write as if you are the actual statute text — use formal legal language, section references,
and the phrase structure of Indian legislation. 2-3 sentences maximum.

This hypothetical passage will be embedded and used to search for real statute sections.
```

**Expected Output:**
```
"Every private company incorporated under this Act shall file the Form INC-12 with the Registrar of Companies within thirty days of incorporation, unless exempted under Rule 6. The Registrar shall maintain a register of all companies incorporated under this provision, and shall issue a certificate of incorporation to each company upon filing of the prescribed form and fees."
```

---

### Entity Extraction

**Purpose:** Extract structured entities from a section for Neo4j.

**Model:** Claude Sonnet

**Prompt:**
```
You are extracting structured legal entities from a section of Indian corporate law.

Section text:
<section>
{section_text}
</section>

Extract all entities of these types. Return ONLY valid JSON, no explanation.

{
  "acts": [{"name": str, "year": int}],
  "sections": [{"number": str, "title": str, "act": str}],
  "definitions": [{"term": str, "definition": str, "defined_in": str}],
  "compliance_obligations": [{
    "name": str,
    "description": str,
    "frequency": str,
    "due_date_logic": str
  }],
  "penalties": [{
    "amount_min": float,
    "amount_max": float,
    "type": str,
    "currency": "INR"
  }],
  "entity_types": [{"name": str}],
  "thresholds": [{"metric": str, "value": float, "unit": str}],
  "authorities": [{"name": str, "type": str}]
}

Return empty lists for entity types not found. Numbers only for amounts (no "lakh" — convert: 5 lakh = 500000).
```

---

### Relation Extraction

**Purpose:** Extract typed relationships between entities.

**Model:** Claude Sonnet

**Prompt:**
```
Given these entities extracted from a legal section, extract relationships between them.

Entities:
{entities_json}

Section text:
<section>
{section_text}
</section>

Return ONLY valid JSON with this exact structure:
{
  "relationships": [
    {
      "from_type": str,
      "from_id": str,
      "relationship": str,
      "to_type": str,
      "to_id": str
    }
  ]
}

Allowed relationships: GOVERNED_BY | APPLIES_TO | HAS_CONDITION | PENALTY_FOR_BREACH | ENFORCED_BY | DEFINES | CROSS_REFERENCES | AMENDED_BY | EXEMPT_FROM | ISSUED_UNDER

Only extract relationships explicitly stated in the text. Do not infer.
```

---

### Contextualization

**Purpose:** Generate 1-2 context sentences for chunk embedding.

**Model:** Claude Haiku

**Prompt:**
```
You are processing a legal document for a RAG retrieval system.

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
```

---

### CRAG Check (Context Quality Evaluation)

**Purpose:** Evaluate whether retrieved context is sufficient.

**Model:** Claude Sonnet

**Prompt:**
```
Evaluate whether the retrieved context is sufficient to answer this query.

Query: {query}

Retrieved context summary:
{context_summary}

Score the context from 0.0 to 1.0:
- 1.0: Context directly and completely answers the query
- 0.7: Context mostly answers the query, minor gaps
- 0.5: Context partially answers, significant gaps
- 0.3: Context is tangentially related, major gaps
- 0.0: Context is irrelevant to the query

Also identify: what specific information is missing (if score < 0.6)?

Return ONLY valid JSON:
{"score": float, "reason": str, "missing_info": str}
```

**Expected Output:**
```json
{
  "score": 0.45,
  "reason": "Context covers annual return filing but missing penalty details for non-compliance",
  "missing_info": "Specific monetary penalties and imprisonment terms for late filing"
}
```

---

### Query Refinement

**Purpose:** Generate refined query based on why retrieval failed.

**Model:** Claude Haiku

**Prompt:**
```
The initial retrieval for a legal query was insufficient. 

Original query: {original_query}

Reason context was insufficient: {refinement_reason}

Generate a refined query that:
1. Preserves the core legal question
2. Incorporates missing context indicators
3. Uses more specific legal terminology if needed
4. May broaden scope to related sections/acts if appropriate

Return ONLY the refined query text, no explanation.
```

---

### Generation (Answer with Citations)

**Purpose:** Generate final answer with inline citations.

**Model:** Claude Sonnet

**Prompt:**
```
You are Clause, a legal AI assistant specialised in Indian startup and corporate law.

You are answering a question using the following retrieved legal context.
Base your answer ONLY on the provided context. Do not use prior knowledge.
If the context does not contain enough information to answer fully, say so explicitly.

Retrieved Context:
{context_blocks}

Question: {query}

Instructions:
1. Answer directly and precisely
2. Cite every claim with the source section in brackets: [Act Name, Section/Rule X]
3. For conditional rules, explicitly state the conditions: "IF [condition] THEN [rule]"
4. If there are exceptions or provisos, state them clearly
5. End with a "Key Sections Referenced" list

Answer:
```

---

## Module Structure

```python
# clause/generation/prompts.py

# ============ QUERY PIPELINE ============
QUERY_CLASSIFICATION_PROMPT = "..."
QUERY_EXPANSION_PROMPT = "..."
HYDE_PROMPT = "..."

# ============ GRAPH EXTRACTION ============
ENTITY_EXTRACTION_PROMPT = "..."
RELATION_EXTRACTION_PROMPT = "..."

# ============ ENRICHMENT ============
CONTEXTUALIZATION_PROMPT = "..."

# ============ AGENT LOOP ============
CRAG_CHECK_PROMPT = "..."
QUERY_REFINEMENT_PROMPT = "..."

# ============ GENERATION ============
GENERATION_PROMPT = "..."
CONTEXT_BLOCK_TEMPLATE = "..."

# ============ USAGE ============
# Import in other modules:
# from clause.generation.prompts import GENERATION_PROMPT, CRAG_CHECK_PROMPT
```

---

## Best Practices

1. **Use f-strings** — Never format prompts at import time
2. **Preserve whitespace** — Multi-line strings are intentional
3. **Test prompts** — Add test cases for each prompt
4. **Version control** — Track prompt changes in git history
5. **Document constraints** — Add comments about JSON return format expectations

---

## Prompt Tuning Notes

**For retrieval quality:**
- QUERY_EXPANSION: More phrasings = higher recall but slower
- HYDE: Length affects embedding quality; 2-3 sentences is optimal

**For graph quality:**
- ENTITY_EXTRACTION: Be specific about JSON structure to avoid malformed outputs
- RELATION_EXTRACTION: List allowed relationships explicitly

**For generation:**
- GENERATION_PROMPT: Instruction order matters (cite first, then conditional logic)
- CRAG_CHECK_PROMPT: Threshold of 0.6 is tunable based on downstream quality

---

## 🔗 Next Steps

- Constraints: [13-CONSTRAINTS.md](13-CONSTRAINTS.md)
- Main architecture: [01-PROJECT-OVERVIEW.md](01-PROJECT-OVERVIEW.md)
