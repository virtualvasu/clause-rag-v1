# 07 — Generation & Citations

Covers Step 9: LLM-based generation and citation extraction.

---

## Generation Prompt

**File**: `clause/generation/prompts.py`

```python
GENERATION_PROMPT = """You are Clause, a legal AI assistant specialised in Indian startup and corporate law.

You are answering a question using the following retrieved legal context.
Base your answer ONLY on the provided context. Do not use prior knowledge.
If the context does not contain enough information to answer fully, say so explicitly.

Retrieved Context:
{context_blocks}

Question: {query}

Instructions:
1. Answer directly and precisely
2. Cite every claim with the source section in brackets: [Companies Act 2013, Section 42(3)]
3. For conditional rules, explicitly state the conditions: "IF [condition] THEN [rule]"
4. If there are exceptions or provisos, state them clearly
5. End with a "Key Sections Referenced" list

Answer:"""

CONTEXT_BLOCK_TEMPLATE = """
---
Source: {act}, {section_number} — {section_title}
{text}
---"""
```

### Generation Logic

**File**: `clause/generation/generator.py`

```python
import anthropic
from clause.config import settings

async def generate_answer(
    query: str,
    context_chunks: list[dict],
    model: str = None
) -> tuple[str, list[dict]]:
    """
    Generate answer using Claude Sonnet with merged context.
    
    Args:
        query: Original user query
        context_chunks: List of dicts with {act, section_number, section_title, text}
        model: LLM model to use (default: settings.generation_model)
    
    Returns:
        (answer_text, citations)
    """
    model = model or settings.generation_model
    
    # Build context blocks
    context_blocks = "\n".join([
        CONTEXT_BLOCK_TEMPLATE.format(
            act=chunk["act"],
            section_number=chunk["section_number"],
            section_title=chunk.get("section_title", ""),
            text=chunk["text"]
        )
        for chunk in context_chunks
    ])
    
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    
    response = client.messages.create(
        model=model,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": GENERATION_PROMPT.format(
                context_blocks=context_blocks,
                query=query
            )
        }]
    )
    
    answer = response.content[0].text
    citations = extract_citations(answer, context_chunks)
    
    return answer, citations
```

---

## Citation Extraction

```python
import re
from typing import Optional

def extract_citations(
    answer: str,
    context_chunks: list[dict]
) -> list[dict]:
    """
    Parse inline citations from generated answer.
    Pattern: [Act Name, Section X]
    Cross-reference with retrieved context for full citation objects.
    """
    citation_pattern = r'\[([^\]]+),\s*(Section|Rule|Regulation)\s+([^\]]+)\]'
    matches = re.findall(citation_pattern, answer)
    
    citations = []
    for act, sec_type, sec_num in matches:
        # Find matching context chunk
        matching_chunk = None
        for chunk in context_chunks:
            if (act.strip() in chunk.get("act", "") and
                sec_num.strip() in chunk.get("section_number", "")):
                matching_chunk = chunk
                break
        
        citation_obj = {
            "act": act.strip(),
            "section_type": sec_type,
            "section_number": sec_num.strip(),
        }
        
        if matching_chunk:
            citation_obj.update({
                "section_title": matching_chunk.get("section_title"),
                "chunk_id": matching_chunk.get("chunk_id"),
                "text_excerpt": matching_chunk.get("text", "")[:200],
            })
        
        citations.append(citation_obj)
    
    return citations
```

---

## Citation Format Examples

**Simple Citation:**
```
Under Section 42 of the Companies Act 2013 [Companies Act 2013, Section 42], 
a company must not issue fresh offers within 60 days of a private placement.
```

**Conditional Citation:**
```
IF [the company is a small company under Section 2(85) of the Companies Act 2013]
THEN [it is exempt from mandatory audit requirements under Rule 3(3) of the 
Companies (Accounts) Rules 2014].
```

**Multi-part Citation:**
```
When issuing CCPS, founders must comply with:
- Section 62 [Companies Act 2013, Section 62] for shareholder approval
- Regulation 26 of SEBI ICDR [SEBI (ICDR) Regulations 2018, Regulation 26] for disclosure
- DPIIT guidelines [DPIIT Startup Recognition Guidelines] for tax benefits
```

---

## Integration with Agent

The `generate_answer` node in the agent calls this function:

```python
# clause/agent/nodes.py

async def generate_answer(state: ClauseState) -> ClauseState:
    """
    Final generation step.
    Takes final_context and generates answer with citations.
    """
    answer, citations = await generate_answer(
        query=state["original_query"],
        context_chunks=state["final_context"]
    )
    
    state["answer"] = answer
    state["citations"] = citations
    
    return state
```

---

## Quality Considerations

1. **Context Freshness** — Use only the current state's `final_context`, not cached
2. **Citation Accuracy** — Verify all citations match actual retrieved chunks
3. **Hallucination Prevention** — The CRAG check ensures context is sufficient before generation
4. **Token Management** — Monitor token usage for cost control
5. **Fallback Handling** — If generation fails, return error state to user

---

## 🔗 Next Steps

- Evaluation framework: [08-EVALUATION.md](08-EVALUATION.md)
- API endpoints: [09-API-FRONTEND.md](09-API-FRONTEND.md)
