"""
All LLM prompt templates as module-level constants.

Rule: NEVER define prompts inline in other files. Always import from here.
Rule: Use .format(**kwargs) at call time, never at import time.
"""

# ============ QUERY PIPELINE ============

QUERY_CLASSIFICATION_PROMPT = """Classify this legal query into exactly one category.

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

Return ONLY one word: SIMPLE, MULTI_HOP, CROSS_DOC, or CONDITIONAL"""


QUERY_EXPANSION_PROMPT = """You are expanding a legal query to improve retrieval coverage.

Original query: {query}

Generate exactly 3 alternative phrasings of this query. Each phrasing should:
1. Use different legal terminology that might appear in the actual statute
2. Cover different angles of the same question
3. Be specific enough to retrieve relevant sections

Legal documents use formal language like "shall", "notwithstanding", "pursuant to".
Include both formal statutory language and plain English variants.

Return ONLY a JSON array of 3 strings:
["phrasing 1", "phrasing 2", "phrasing 3"]"""


HYDE_PROMPT = """Write a short passage that would appear in an Indian legal document
(Companies Act, SEBI regulation, or MCA rule) that directly answers this question:

Question: {query}

Write as if you are the actual statute text — use formal legal language, section references,
and the phrase structure of Indian legislation. 2-3 sentences maximum.

This hypothetical passage will be embedded and used to search for real statute sections."""


# ============ AGENT LOOP ============

CRAG_CHECK_PROMPT = """Evaluate whether the retrieved context is sufficient to answer this query.

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
{{"score": float, "reason": str, "missing_info": str}}"""


QUERY_REFINEMENT_PROMPT = """The initial retrieval for a legal query was insufficient.

Original query: {original_query}

Reason context was insufficient: {refinement_reason}

Generate a refined query that:
1. Preserves the core legal question
2. Incorporates missing context indicators
3. Uses more specific legal terminology if needed
4. May broaden scope to related sections/acts if appropriate

Return ONLY the refined query text, no explanation."""


# ============ GENERATION ============

CONTEXT_BLOCK_TEMPLATE = """---
Source: {act} | Section {section_number}{section_title_part}
{text}
---"""

GENERATION_PROMPT = """You are Clause, a legal AI assistant specialised in Indian startup and corporate law.

You are answering a question using the following retrieved legal context.
Base your answer ONLY on the provided context. Do not use prior knowledge.
If the context does not contain enough information to answer fully, say so explicitly.

Retrieved Context:
{context_blocks}

Question: {query}

Instructions:
1. Answer directly and precisely
2. Cite every claim with the source section in brackets: [Act Name, Section X]
3. For conditional rules, explicitly state the conditions: "IF [condition] THEN [rule]"
4. If there are exceptions or provisos, state them clearly
5. End with a "Key Sections Referenced" list

Answer:"""


# ============ ENRICHMENT (used by ingestion pipeline) ============

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
"This sub-section is from Section 42(3) of the Companies Act 2013, governing the 60-day cooling period between private placements. It specifies the restriction on issuing fresh offers within this period." """
