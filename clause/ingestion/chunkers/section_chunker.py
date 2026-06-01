"""Section-based legal text chunking with hierarchy."""

import re
import logging
from typing import Optional
from clause.ingestion.chunkers import LegalChunk, ACT_ABBREVIATIONS

logger = logging.getLogger(__name__)

# Regex separators in priority order — never change this order
LEGAL_SEPARATORS = [
    r'\n(?=Section\s+\d+[A-Z]?\b)',     # "Section 42" — primary boundary
    r'\n(?=\d+[A-Z]?\.\s)',             # "42. Short title" — numbered sections
    r'\n(?=\(\d+\)\s)',                 # "(1) Every company shall..." — sub-sections
    r'\n(?=\([a-z]\)\s)',               # "(a) the company..." — clauses
    r'\n(?=Provided\s+that)',           # Proviso start — flag, do not split here
    r'(?<=\.)\s{2,}(?=[A-Z])',          # Sentence boundary fallback
]

# Cross-reference patterns to detect and store
CROSS_REF_PATTERNS = [
    r'[Ss]ection\s+\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\))?',   # "Section 42(3)(a)"
    r'[Ss]ub-?[Ss]ection\s+\(\d+\)',                        # "sub-section (3)"
    r'[Rr]ule\s+\d+[A-Z]?',                                 # "Rule 14A"
    r'[Ss]chedule\s+[IVXLC]+',                              # "Schedule IV"
    r'[Ff]orm\s+[A-Z]+-\d+[A-Z]?',                          # "Form MGT-7"
    r'[Cc]lause\s+\(\d+\)',                                 # "clause (3)"
]


def extract_cross_references(text: str) -> list[str]:
    """
    Extract all cross-references from text.
    Returns list of unique references found.
    """
    references = set()
    for pattern in CROSS_REF_PATTERNS:
        matches = re.findall(pattern, text)
        references.update(matches)
    return sorted(list(references))


def count_tokens(text: str) -> int:
    """
    Estimate token count using simple word-based heuristic.
    In production, use tiktoken for cl100k_base encoding.
    Formula: ~1.3 tokens per word on average for English.
    """
    words = len(text.split())
    return int(words * 1.3)


def split_by_legal_structure(text: str) -> list[str]:
    """
    Split text into sections using all legal regex separators combined.

    Builds a single combined pattern from all separators so that every
    boundary in the document is found in one pass — not just the first
    occurrence of each separator type.
    """
    # Combine all separators with alternation so re.split finds ALL boundaries
    combined_pattern = "|".join(f"(?:{sep})" for sep in LEGAL_SEPARATORS)
    parts = re.split(combined_pattern, text)
    return [p.strip() for p in parts if p and p.strip()]


def is_proviso(text: str) -> bool:
    """Check if chunk starts with proviso (cannot be standalone)."""
    return text.strip().startswith(("Provided that", "Provided further that"))


def is_explanation(text: str) -> bool:
    """Check if chunk starts with explanation (cannot be standalone)."""
    return text.strip().startswith("Explanation")


def merge_dependent_chunks(chunks: list[str]) -> list[str]:
    """
    Merge chunks that cannot stand alone (provisos, explanations).
    These must be merged with their preceding chunk.
    """
    merged = []
    i = 0
    while i < len(chunks):
        current = chunks[i]
        # Look ahead and merge dependent chunks
        while i + 1 < len(chunks) and (is_proviso(chunks[i + 1]) or is_explanation(chunks[i + 1])):
            current += "\n" + chunks[i + 1]
            i += 1
        merged.append(current)
        i += 1
    return merged


def create_table_chunks(
    tables: list[dict],
    act: str,
    act_abbr: str,
    source_file: str,
) -> list[LegalChunk]:
    """
    Create type="table" chunks from extracted table data.
    Table chunks are never split — the whole table is one chunk.

    Rule 4: Tables belong to the document, not individual sections.
    chunk_id format: ACT_T{n}  e.g. CA2013_T1
    """
    table_chunks = []
    for idx, table in enumerate(tables, 1):
        chunk_id = f"{act_abbr}_T{idx}"
        raw_text = table.get("raw", "")
        tokens = count_tokens(raw_text)

        table_chunk = LegalChunk(
            chunk_id=chunk_id,
            type="table",
            act=act,
            text=raw_text,
            contextualized_text=raw_text,  # Tables are used as-is
            cross_references=[],
            tokens=tokens,
            source_file=source_file,
        )
        table_chunks.append(table_chunk)
    return table_chunks


def create_legal_chunks(
    text: str,
    act: str,
    chapter: Optional[str] = None,
    source_file: str = "unknown.pdf",
    tables: Optional[list[dict]] = None,
) -> list[LegalChunk]:
    """
    Create hierarchical legal chunks from parsed text.

    Process:
    1. Split by legal structure (sections, sub-sections, clauses)
    2. Merge dependent chunks (provisos, explanations)
    3. Create parent chunks (one full section)
    4. Create child chunks from parent (sub-sections)
    5. Create table chunks (never split) — Rule 4
    6. Validate token bounds
    7. Extract cross-references
    """
    # Abbreviate act name
    act_abbr = ACT_ABBREVIATIONS.get(act, act[:6].upper())

    # Split into sections using all separators in a single combined pass
    section_texts = split_by_legal_structure(text)
    section_texts = merge_dependent_chunks(section_texts)

    chunks = []
    section_counter = 0

    for section_text in section_texts:
        section_counter += 1
        section_text = section_text.strip()

        if not section_text:
            continue

        # Extract section number from first line
        section_number_match = re.match(r'Section\s+(\d+[A-Z]?)', section_text)
        section_number = section_number_match.group(1) if section_number_match else f"{section_counter}"

        # Extract section title (often on first or second line after section number)
        lines = section_text.split('\n')
        section_title = ""
        if len(lines) > 1:
            section_title = lines[1].strip() if not lines[1].strip().startswith('(') else ""

        # Create parent chunk for the full section
        parent_chunk_id = f"{act_abbr}_S{section_number}"
        tokens_parent = count_tokens(section_text)

        # Warn if parent exceeds bounds — Rule 5 (never silently truncate)
        if tokens_parent > 1024:
            logger.warning(
                f"Parent chunk {parent_chunk_id} exceeds 1024 tokens ({tokens_parent}). "
                "Consider splitting at sub-section boundary."
            )

        parent_chunk = LegalChunk(
            chunk_id=parent_chunk_id,
            type="parent",
            act=act,
            chapter=chapter,
            section_number=section_number,
            section_title=section_title,
            text=section_text,
            contextualized_text=None,  # Set by enrichment
            cross_references=extract_cross_references(section_text),
            tokens=tokens_parent,
            source_file=source_file,
        )
        chunks.append(parent_chunk)

        # Create child chunks from sub-sections (lines starting with "(1)", "(a)", etc.)
        sub_section_pattern = r'\n(?=\([\d\w]+\)\s)'
        sub_sections = re.split(sub_section_pattern, section_text)

        child_counter = 0
        for sub_text in sub_sections:
            sub_text = sub_text.strip()
            if not sub_text or len(sub_text) < 20:  # Skip trivial chunks
                continue

            child_counter += 1
            child_chunk_id = f"{parent_chunk_id}_{child_counter}"
            tokens_child = count_tokens(sub_text)

            # Warn if outside bounds — Rule 5, never silently truncate
            if tokens_child < 128:
                logger.warning(f"Child chunk {child_chunk_id} below 128 tokens ({tokens_child})")
            elif tokens_child > 256:
                logger.warning(f"Child chunk {child_chunk_id} exceeds 256 tokens ({tokens_child})")

            child_chunk = LegalChunk(
                chunk_id=child_chunk_id,
                type="child",
                parent_id=parent_chunk_id,
                act=act,
                chapter=chapter,
                section_number=section_number,
                section_title=section_title,
                text=sub_text,
                contextualized_text=None,  # Set by enrichment
                cross_references=extract_cross_references(sub_text),
                tokens=tokens_child,
                source_file=source_file,
            )
            chunks.append(child_chunk)

    # Rule 4: Create table chunks once per document — tables belong to the
    # document, not individual sections. Must be outside the section loop.
    if tables:
        table_chunks = create_table_chunks(
            tables=tables,
            act=act,
            act_abbr=act_abbr,
            source_file=source_file,
        )
        chunks.extend(table_chunks)
        logger.info(f"Created {len(table_chunks)} table chunk(s) from {source_file}")

    return chunks
