"""Document chunking — hierarchical, legal-aware text splitting."""

from pydantic import BaseModel
from typing import Optional


class LegalChunk(BaseModel):
    """
    Represents a chunk of legal text at any hierarchy level.

    Three types of chunks form a hierarchy:
    - document: metadata only, populates Neo4j Act nodes
    - parent: one complete section (512-1024 tokens), sent to LLM at generation
    - child: one sub-section/clause (128-256 tokens), embedded and retrieved
    - table: structured table, never split
    """

    chunk_id: str
    """Deterministic ID. Format: ACT_S{n} or ACT_S{n}_{m}"""

    type: str
    """One of: "document", "parent", "child", "table" """

    parent_id: Optional[str] = None
    """Only set on child chunks. Points to parent chunk ID."""

    act: str
    """Act name. e.g. "Companies Act 2013" """

    chapter: Optional[str] = None
    """Chapter name. e.g. "Chapter II" """

    section_number: Optional[str] = None
    """Section/Rule number. e.g. "42", "42(3)", "Rule 14" """

    section_title: Optional[str] = None
    """Full section title. e.g. "Private Placements" """

    text: str
    """Original text — shown in citations. Never modified."""

    contextualized_text: Optional[str] = None
    """Set by enrichment. Prepends 1-2 context sentences. Used for embedding."""

    cross_references: list[str] = []
    """Detected references. e.g. ["Section 43", "Rule 14"] — become graph edges."""

    tokens: int
    """Token count of original text. Validated against bounds."""

    source_file: str
    """Source PDF or HTML filename."""

    sentence_window: Optional[str] = None
    """±2 sentences around child chunk for context."""

    class Config:
        # Allow arbitrary types for compatibility
        arbitrary_types_allowed = True


# Act abbreviations (locked — from architecture doc)
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
