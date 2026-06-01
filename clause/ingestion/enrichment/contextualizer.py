"""Contextual enrichment — supports Claude (cloud) or Ollama (local)."""

import asyncio
import logging
from typing import Optional

from clause.config import settings
from clause.ingestion.chunkers import LegalChunk

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Claude provider
# ---------------------------------------------------------------------------

async def _contextualize_with_claude(
    child: LegalChunk,
    parent: LegalChunk,
    client,  # anthropic.AsyncAnthropic
    model: str,
) -> LegalChunk:
    """Contextualize a chunk using Claude (Anthropic API)."""
    import anthropic

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": CONTEXTUALIZATION_PROMPT.format(
                    act_name=child.act,
                    parent_text=parent.text,
                    chunk_text=child.text,
                ),
            }],
        )
        context_sentence = response.content[0].text.strip()
        child.contextualized_text = f"{context_sentence}\n\n{child.text}"
        logger.debug(f"[claude] Contextualized {child.chunk_id}")
        return child

    except anthropic.APIError as e:
        logger.error(f"[claude] Error contextualizing {child.chunk_id}: {e}")
        child.contextualized_text = child.text
        return child


# ---------------------------------------------------------------------------
# Ollama provider (OpenAI-compatible endpoint)
# ---------------------------------------------------------------------------

async def _contextualize_with_ollama(
    child: LegalChunk,
    parent: LegalChunk,
    client,  # openai.AsyncOpenAI pointed at Ollama
    model: str,
) -> LegalChunk:
    """Contextualize a chunk using a local Ollama model."""
    try:
        response = await client.chat.completions.create(
            model=model,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": CONTEXTUALIZATION_PROMPT.format(
                    act_name=child.act,
                    parent_text=parent.text,
                    chunk_text=child.text,
                ),
            }],
        )
        context_sentence = response.choices[0].message.content.strip()
        child.contextualized_text = f"{context_sentence}\n\n{child.text}"
        logger.debug(f"[ollama] Contextualized {child.chunk_id}")
        return child

    except Exception as e:
        logger.error(f"[ollama] Error contextualizing {child.chunk_id}: {e}")
        child.contextualized_text = child.text
        return child


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def contextualize_chunk(
    child: LegalChunk,
    parent: LegalChunk,
    client,
    model: str,
) -> LegalChunk:
    """
    Generate context sentence for a child chunk using its parent section.

    Routes to Claude or Ollama based on settings.enrichment_provider.
    """
    if settings.enrichment_provider == "ollama":
        return await _contextualize_with_ollama(child, parent, client, model)
    else:
        return await _contextualize_with_claude(child, parent, client, model)


async def contextualize_all(
    children: list[LegalChunk],
    parent_map: dict[str, LegalChunk],
    concurrency: int = 10,
) -> list[LegalChunk]:
    """
    Contextualize all child chunks with controlled concurrency.

    Provider is selected from settings.enrichment_provider:
    - "ollama" → local Ollama model (free, no API key needed)
    - "claude" → Claude Haiku via Anthropic API (~$1-2 for full corpus)

    concurrency=10 is safe for both Haiku rate limits and local Ollama.

    Args:
        children:    List of child chunks to contextualize
        parent_map:  Dict mapping parent_id → parent LegalChunk
        concurrency: Max parallel calls (default: 10)

    Returns:
        List of contextualized child chunks
    """
    provider = settings.enrichment_provider
    logger.info(f"Enrichment provider: {provider}")

    if provider == "ollama":
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama",  # Ollama doesn't need a real key
        )
        model = settings.ollama_model
        logger.info(f"Using Ollama model: {model} at {settings.ollama_base_url}")
    else:
        import anthropic
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when enrichment_provider=claude. "
                "Set it in .env or switch to enrichment_provider=ollama."
            )
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        model = settings.contextualization_model
        logger.info(f"Using Claude model: {model}")

    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_contextualize(child: LegalChunk) -> LegalChunk:
        async with semaphore:
            parent = parent_map.get(child.parent_id)
            if not parent:
                logger.warning(f"Parent not found for {child.chunk_id}, using text as-is")
                child.contextualized_text = child.text
                return child
            return await contextualize_chunk(child, parent, client, model)

    logger.info(f"Contextualizing {len(children)} child chunks with concurrency={concurrency}")
    tasks = [bounded_contextualize(child) for child in children]
    return await asyncio.gather(*tasks)
