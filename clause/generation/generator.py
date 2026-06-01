"""
Answer generation with inline citation extraction.

Generation providers (routed by config):
  "ollama"  → qwen2.5:7b via Ollama (local, free) — default
  "claude"  → claude-sonnet-4 via Anthropic API (paid, best quality)
"""

import json
import logging
import re
from typing import Optional

from clause.config import settings
from clause.generation.prompts import (
    GENERATION_PROMPT,
    CONTEXT_BLOCK_TEMPLATE,
    CRAG_CHECK_PROMPT,
    QUERY_REFINEMENT_PROMPT,
)

logger = logging.getLogger(__name__)


# ── Context formatting ─────────────────────────────────────────────────────────

def format_context_blocks(chunks: list[dict]) -> str:
    """Format retrieved chunks into numbered context blocks for the LLM prompt."""
    blocks = []
    for chunk in chunks:
        section_title = chunk.get("section_title", "")
        section_title_part = f" — {section_title}" if section_title else ""
        block = CONTEXT_BLOCK_TEMPLATE.format(
            act=chunk.get("act", "Unknown Act"),
            section_number=chunk.get("section_number", ""),
            section_title_part=section_title_part,
            text=chunk.get("text", ""),
        )
        blocks.append(block)
    return "\n".join(blocks)


# ── LLM backends ──────────────────────────────────────────────────────────────

def _call_ollama(prompt: str, max_tokens: int = 1000) -> str:
    """Call Ollama local LLM (OpenAI-compatible API)."""
    from openai import OpenAI

    client = OpenAI(
        base_url=settings.ollama_base_url,
        api_key="ollama",  # required by client but unused
    )
    response = client.chat.completions.create(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.1,  # low temp for factual legal answers
    )
    return response.choices[0].message.content.strip()


def _call_claude(prompt: str, max_tokens: int = 1000) -> str:
    """Call Claude via Anthropic API."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.generation_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _llm_call(prompt: str, max_tokens: int = 1000) -> str:
    """Route LLM call based on enrichment_provider config (reusing same setting)."""
    provider = settings.enrichment_provider
    if provider == "claude":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set — use enrichment_provider=ollama")
        return _call_claude(prompt, max_tokens)
    else:
        return _call_ollama(prompt, max_tokens)


# ── Citation extraction ────────────────────────────────────────────────────────

def extract_citations(answer: str, context_chunks: list[dict]) -> list[dict]:
    """
    Parse inline citations from generated answer text.

    Matches patterns like:
      [Companies Act 2013, Section 42]
      [SEBI ICDR Regulations 2018, Regulation 26]
      [DPIIT Guidelines, Section 5]
    """
    citation_pattern = r'\[([^\]]+),\s*(Section|Rule|Regulation|Clause)\s+([^\]]+)\]'
    matches = re.findall(citation_pattern, answer)

    citations = []
    seen = set()

    for act, sec_type, sec_num in matches:
        key = f"{act.strip()}_{sec_num.strip()}"
        if key in seen:
            continue
        seen.add(key)

        citation_obj = {
            "act": act.strip(),
            "section_type": sec_type,
            "section_number": sec_num.strip(),
        }

        # Try to match to a retrieved chunk
        for chunk in context_chunks:
            if (
                act.strip().lower() in chunk.get("act", "").lower()
                and sec_num.strip() in chunk.get("section_number", "")
            ):
                citation_obj.update({
                    "section_title": chunk.get("section_title"),
                    "chunk_id": chunk.get("chunk_id"),
                    "text_excerpt": chunk.get("text", "")[:200],
                })
                break

        citations.append(citation_obj)

    return citations


# ── Main generation function ───────────────────────────────────────────────────

def generate_answer(
    query: str,
    context_chunks: list[dict],
    max_tokens: int = 1000,
) -> dict:
    """
    Generate a legal answer with inline citations from retrieved chunks.

    Args:
        query:          Original user question
        context_chunks: Reranked chunks from hybrid_retrieve()
        max_tokens:     Max response length

    Returns:
        {
            "answer":    str   — full answer text with inline citations
            "citations": list  — structured citation objects
            "provider":  str   — which LLM was used
            "chunks_used": int — number of context chunks
        }
    """
    if not context_chunks:
        return {
            "answer": "I could not find relevant legal context to answer your question.",
            "citations": [],
            "provider": settings.enrichment_provider,
            "chunks_used": 0,
        }

    context_blocks = format_context_blocks(context_chunks)

    prompt = GENERATION_PROMPT.format(
        context_blocks=context_blocks,
        query=query,
    )

    logger.info(
        f"Generating answer | provider={settings.enrichment_provider} "
        f"| chunks={len(context_chunks)} | query='{query[:60]}...'"
    )

    answer = _llm_call(prompt, max_tokens=max_tokens)
    citations = extract_citations(answer, context_chunks)

    logger.info(f"Generated answer ({len(answer)} chars, {len(citations)} citations)")

    return {
        "answer": answer,
        "citations": citations,
        "provider": settings.enrichment_provider,
        "chunks_used": len(context_chunks),
    }


# ── CRAG context quality check ─────────────────────────────────────────────────

def crag_check(query: str, context_chunks: list[dict]) -> dict:
    """
    Evaluate whether retrieved context is sufficient to answer the query.
    Returns score 0-1 and reason. Used by the agent loop.

    Score >= 0.6 → proceed to generation
    Score <  0.6 → refine query and re-retrieve
    """
    # Build a compact summary of context (just section refs + first 100 chars each)
    context_summary = "\n".join([
        f"- {c.get('act')} Section {c.get('section_number')}: {c.get('text', '')[:100]}..."
        for c in context_chunks[:10]
    ])

    prompt = CRAG_CHECK_PROMPT.format(
        query=query,
        context_summary=context_summary,
    )

    raw = _llm_call(prompt, max_tokens=200)

    try:
        # Extract JSON from response (LLM may wrap it in markdown)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        result = json.loads(json_match.group()) if json_match else {}
        return {
            "score": float(result.get("score", 0.5)),
            "reason": result.get("reason", ""),
            "missing_info": result.get("missing_info", ""),
        }
    except (json.JSONDecodeError, AttributeError):
        logger.warning(f"CRAG check failed to parse JSON: {raw[:100]}")
        return {"score": 0.5, "reason": "parse error", "missing_info": ""}


def refine_query(original_query: str, refinement_reason: str) -> str:
    """Generate a refined query to improve retrieval on retry."""
    prompt = QUERY_REFINEMENT_PROMPT.format(
        original_query=original_query,
        refinement_reason=refinement_reason,
    )
    return _llm_call(prompt, max_tokens=150)
