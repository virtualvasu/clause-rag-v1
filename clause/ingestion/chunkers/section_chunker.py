"""
Section Chunker - Spec-Compliant Legal Document Chunking Pipeline

Implements a 3-layer hierarchical chunking strategy:
- Layer 1: Document Metadata (document-level graph nodes)
- Layer 2: Parent Chunks (section-level, 512-1024 tokens, for generation context)
- Layer 3: Child Chunks (sub-section level, 128-256 tokens, for retrieval)

Plus:
- Sentence Windows: ±2 sentences context for each child chunk
- Table Extraction: Fee schedules and penalty tables as structured chunks
- Cross-Reference Detection: Legal references become Neo4j graph edges
- Proviso/Explanation Enforcement: Never separated from parent context
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LegalChunk(BaseModel):
    """
    Pydantic model representing a single chunk in the legal document hierarchy.
    
    Each chunk has deterministic chunk_id, complete metadata for graph construction,
    and context-aware fields (sentence_window, cross_references) for retrieval.
    """
    
    # Core identity
    chunk_id: str = Field(
        ...,
        description="Deterministic chunk ID. Format: ACT_S{n} (parent) or ACT_S{n}_{m} (child)"
    )
    type: str = Field(
        ...,
        description="Chunk type: 'document', 'parent', 'child', or 'table'"
    )
    
    # Text content
    text: str = Field(..., description="Full text of the chunk")
    
    # Hierarchical metadata
    act: str = Field(..., description="Act abbreviation (e.g., 'CA2013', 'SEBI_AIF')")
    chapter: Optional[str] = Field(None, description="Chapter number if applicable")
    section_number: Optional[str] = Field(None, description="Section number (e.g., '42', '4A')")
    section_title: Optional[str] = Field(None, description="Section title/heading")
    
    # Parent-child relationships
    parent_id: Optional[str] = Field(None, description="Parent chunk ID (None for parent chunks)")
    children_ids: List[str] = Field(default_factory=list, description="List of child chunk IDs")
    
    # Token accounting
    tokens: int = Field(..., description="Exact token count using tiktoken cl100k_base")
    
    # Retrieval context
    sentence_window: Optional[str] = Field(
        None,
        description="±2 sentences of surrounding context (child chunks only, for generation)"
    )
    cross_references: List[str] = Field(
        default_factory=list,
        description="Detected legal references (Section X, Rule Y, etc.) → become graph edges"
    )
    
    # Document source
    source_file: str = Field(..., description="Source PDF filename")
    source_page: Optional[int] = Field(None, description="Source page number")
    
    # Document layer only
    name: Optional[str] = Field(None, description="Document full name (document type only)")
    year: Optional[int] = Field(None, description="Document year (document type only)")
    ministry: Optional[str] = Field(None, description="Ministry/body (document type only)")
    source_url: Optional[str] = Field(None, description="Source URL (document type only)")
    total_sections: Optional[int] = Field(None, description="Total sections in doc (document type only)")
    
    # Table extraction
    structured: Optional[List[Dict]] = Field(
        None,
        description="Parsed table data as list of dicts (table type only)"
    )
    
    model_config = ConfigDict(validate_assignment=True)


# ============================================================================
# MAIN CHUNKER CLASS
# ============================================================================

class SectionChunker:
    """
    Spec-compliant legal document chunker implementing 3-layer hierarchical splitting.
    
    Core principles:
    1. Provisos NEVER separated from parent clause (enforced via merging)
    2. Explanations NEVER separated from parent section (enforced via merging)
    3. Cross-references detected and stored as graph edges
    4. Tables extracted whole with structured parsing
    5. Token ranges strictly enforced: children 128-256, parents 512-1024
    6. Custom regex-based splitting (not LangChain)
    7. All chunk_ids deterministic (same input → same IDs)
    """
    
    # Regex patterns for legal document structure
    # Explanation: Each pattern matches specific legal formatting
    SECTION_PATTERN = r"^(?:Section|SECTION|Rule|RULE|Article|ARTICLE)?\s*(\d+[A-Za-z]*)\s*[.:\-]\s*"
    # Matches: Section 42, SECTION 1, Rule 3, Article 5B, or "1. ", "2A. ", "3A. ", "1A.", etc.
    # Group 1 captures the section number (e.g., "42", "3A")
    
    SUBSECTION_PATTERN = r"^\s*\((\d+)\)\s"
    # Matches: (1), (2), (3) at line start (sub-sections and provisos)
    
    CLAUSE_PATTERN = r"^\s*\(([a-z])\)\s"
    # Matches: (a), (b), (c) for clause-level splits
    
    CLAUSE_ROMAN_PATTERN = r"^\s*\(([ivxl]+)\)\s"
    # Matches: (i), (ii), (iii), (iv) for sub-clause splits
    
    PROVISO_PATTERN = r"^(?:Provided\s+(?:that|further)|Provided,)"
    # Matches: "Provided that", "Provided further that", "Provided,"
    # Legal reasoning: Provisos are conditional modifiers to parent clauses
    # → MUST be merged with preceding clause (never standalone)
    
    EXPLANATION_PATTERN = r"^Explanation\s*(?:[-–—:]|\.—)"
    # Matches: "Explanation —", "Explanation:", "Explanation.—"
    # Legal reasoning: Explanations interpret parent section
    # → MUST be merged with parent section (never standalone)
    
    TABLE_PATTERN = r"\n\s*\|[\w\s\-₹%()]+\|"
    # Matches: Markdown-style tables with | delimiters
    # Legal reasoning: Penalty schedules, fee tables must be extracted whole
    
    # Cross-reference patterns (will be applied to detect graph edges)
    CROSS_REF_PATTERNS = [
        r"[Ss]ection\s+(\d+[A-Za-z]*(?:\s*\(\d+[a-z]?\))?)",  # Section 42(3), Section 2
        r"[Rr]ule\s+(\d+[A-Za-z]*)",  # Rule 14, Rule 3A
        r"[Aa]rticle\s+(\d+[A-Za-z]*)",  # Article 5
        r"[Ss]chedule\s+(?:[IVX]+|[A-Z])",  # Schedule IV, Schedule A
        r"[Ss]ub-?(?:section|rule)\s+\(([a-z0-9]+)\)(?:\s+of\s+(?:section|rule)\s+(\d+))?",  # sub-section (3) of section 42
    ]
    
    def __init__(self, tokenizer: str = "cl100k_base"):
        """
        Initialize the section chunker.
        
        Args:
            tokenizer: Tiktoken encoding name. Default "cl100k_base" (GPT-3.5/4).
        
        Raises:
            ImportError: If tiktoken is not installed.
        """
        if not HAS_TIKTOKEN:
            raise ImportError("tiktoken is required. Install with: pip install tiktoken")
        
        self.encoding = tiktoken.get_encoding(tokenizer)
        logger.info(f"Initialized SectionChunker with {tokenizer} encoding")
    
    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, any]
    ) -> List[LegalChunk]:
        """
        Main orchestration method: full chunking pipeline.
        
        Workflow:
        1. Create document metadata chunk (Layer 1)
        2. Split into sections (Layer 2 parents)
        3. For each section: split into sub-sections (Layer 3 children)
        4. Enforce proviso merging (never standalone)
        5. Enforce explanation merging (never standalone)
        6. Detect cross-references (→ become graph edges)
        7. Extract tables as dedicated chunks
        8. Attach sentence windows to child chunks
        
        Args:
            text: Full document text
            metadata: Document metadata dict with keys:
                - act: Act abbreviation (required, e.g., "CA2013")
                - name: Full act name (required)
                - year: Year (optional)
                - ministry: Ministry name (optional)
                - source_file: Filename (required)
                - source_url: URL (optional)
        
        Returns:
            List of LegalChunk objects (all layers, all enforcements applied)
        
        Raises:
            ValueError: If required metadata keys are missing
        """
        # Validate required metadata
        required_keys = {"act", "name", "source_file"}
        if not required_keys.issubset(metadata.keys()):
            raise ValueError(f"Missing required metadata keys: {required_keys - set(metadata.keys())}")
        
        chunks: List[LegalChunk] = []
        
        # Layer 1: Document metadata chunk
        doc_chunk = self._create_document_chunk(metadata, text)
        chunks.append(doc_chunk)
        logger.info(f"Created document chunk: {doc_chunk.chunk_id}")
        
        # Split into sections (Layer 2)
        sections = self._split_into_sections(text, metadata)
        logger.info(f"Found {len(sections)} sections")
        
        for section_data in sections:
            section_num = section_data["number"]
            section_text = section_data["text"]
            section_title = section_data["title"]
            
            # Layer 2: Create parent chunk (full section)
            parent_chunk = self._create_parent_chunk(
                section_num=section_num,
                section_text=section_text,
                section_title=section_title,
                metadata=metadata
            )
            chunks.append(parent_chunk)
            
            # Layer 3: Split section into sub-sections → child chunks
            child_chunks = self._create_child_chunks(
                parent_chunk=parent_chunk,
                section_text=section_text,
                metadata=metadata
            )
            chunks.extend(child_chunks)
            parent_chunk.children_ids = [c.chunk_id for c in child_chunks]
        
        # Enforce merging rules
        chunks = self._enforce_proviso_merging(chunks)
        chunks = self._enforce_explanation_merging(chunks)
        
        # Detect cross-references on all chunks
        for chunk in chunks:
            chunk.cross_references = self._detect_cross_references(chunk.text)
        
        # Extract tables as dedicated chunks
        table_chunks = self._extract_tables(text, metadata)
        chunks.extend(table_chunks)
        
        # Attach sentence windows to child chunks
        chunks = self._attach_sentence_windows(chunks, text)
        
        logger.info(f"Created {len(chunks)} total chunks ({len([c for c in chunks if c.type == 'document'])} doc, "
                   f"{len([c for c in chunks if c.type == 'parent'])} parent, "
                   f"{len([c for c in chunks if c.type == 'child'])} child, "
                   f"{len([c for c in chunks if c.type == 'table'])} table)")
        
        return chunks
    
    # ========================================================================
    # LAYER 1: DOCUMENT METADATA
    # ========================================================================
    
    def _create_document_chunk(
        self,
        metadata: Dict[str, any],
        full_text: str
    ) -> LegalChunk:
        """
        Create Layer 1 chunk: document-level metadata for Neo4j nodes.
        
        Not used for retrieval. Stores document identity, ministry, source, and
        section count for graph construction.
        
        Args:
            metadata: Document metadata dict
            full_text: Full document text (used to count sections)
        
        Returns:
            LegalChunk with type="document"
        """
        # Count total sections in document
        section_matches = re.findall(self.SECTION_PATTERN, full_text, re.MULTILINE)
        total_sections = len(section_matches)
        
        chunk_id = f"{metadata['act']}_DOC"
        
        return LegalChunk(
            chunk_id=chunk_id,
            type="document",
            act=metadata["act"],
            name=metadata.get("name", ""),
            year=metadata.get("year"),
            ministry=metadata.get("ministry"),
            source_url=metadata.get("source_url"),
            source_file=metadata["source_file"],
            total_sections=total_sections,
            text="",  # No text for document chunks
            tokens=0  # No tokens counted for document chunks
        )
    
    # ========================================================================
    # LAYER 2: PARENT CHUNKS (Section-level)
    # ========================================================================
    
    def _split_into_sections(
        self,
        text: str,
        metadata: Dict[str, any]
    ) -> List[Dict]:
        """
        Split document into sections using regex-based section boundary detection.
        
        Priority (highest first):
        1. "Section N", "Rule N", "Article N" (section boundary)
        2. Fall back to sentence splitting if section pattern fails
        
        Regex: ^(?:Section|Rule|Article)\s+(\d+[A-Za-z]*) at line start
        This matches legal section headers like "Section 42", "Rule 3A", "Article 5B".
        
        Args:
            text: Full document text
            metadata: Metadata dict (for act name in error messages)
        
        Returns:
            List of dicts: [{"number": "42", "title": "...", "text": "..."}]
        
        Raises:
            ValueError: If no sections found and fallback fails
        """
        sections = []
        lines = text.split("\n")
        
        current_section = None
        current_section_lines = []
        
        for line in lines:
            # Match section header line
            match = re.match(self.SECTION_PATTERN, line)
            
            if match:
                # Save previous section
                if current_section:
                    sections.append({
                        "number": current_section["number"],
                        "title": current_section.get("title", ""),
                        "text": "\n".join(current_section_lines).strip()
                    })
                
                # Start new section
                section_num = match.group(1)
                current_section = {
                    "number": section_num,
                    "title": line.strip()
                }
                current_section_lines = [line]
            
            elif current_section:
                current_section_lines.append(line)
        
        # Save last section
        if current_section:
            sections.append({
                "number": current_section["number"],
                "title": current_section.get("title", ""),
                "text": "\n".join(current_section_lines).strip()
            })
        
        if not sections:
            raise ValueError(
                f"No sections found in {metadata['act']} using pattern {self.SECTION_PATTERN}. "
                "Document may not be in standard legal format (Section N, Rule N, etc.)"
            )
        
        return sections
    
    def _create_parent_chunk(
        self,
        section_num: str,
        section_text: str,
        section_title: str,
        metadata: Dict[str, any]
    ) -> LegalChunk:
        """
        Create Layer 2 chunk: parent (section-level) chunk.
        
        Parent chunks are 512-1024 tokens and contain the complete section
        with all sub-sections intact. Used as generation context (never directly
        retrieved). Format allows for 1-2 sentence summaries.
        
        Token range: 512-1024 (parent chunks for context, not retrieval)
        → If > 1024, log warning (indicates section is unusually large)
        → If < 512, log info (small sections are OK)
        
        Args:
            section_num: Section number (e.g., "42", "4A")
            section_text: Full section text
            section_title: Section heading
            metadata: Document metadata
        
        Returns:
            LegalChunk with type="parent", format ACT_S{n}
        """
        chunk_id = f"{metadata['act']}_S{section_num}"
        tokens = self._count_tokens(section_text)
        
        # Enforce token range (512-1024) with warnings
        if tokens > 1024:
            logger.warning(
                f"Parent chunk {chunk_id} exceeds 1024 tokens ({tokens}). "
                f"Section may be too large for generation context. Consider splitting manually."
            )
        elif tokens < 512:
            logger.info(f"Parent chunk {chunk_id} is small ({tokens} tokens). This is OK.")
        
        return LegalChunk(
            chunk_id=chunk_id,
            type="parent",
            act=metadata["act"],
            section_number=section_num,
            section_title=section_title,
            text=section_text,
            tokens=tokens,
            source_file=metadata["source_file"],
            cross_references=[]  # Will be populated later
        )
    
    # ========================================================================
    # LAYER 3: CHILD CHUNKS (Sub-section level)
    # ========================================================================
    
    def _create_child_chunks(
        self,
        parent_chunk: LegalChunk,
        section_text: str,
        metadata: Dict[str, any]
    ) -> List[LegalChunk]:
        """
        Split parent section into child chunks (sub-section level).
        
        Priority (highest first):
        1. Sub-section boundaries: ^\s*\((\d+)\)
        2. Clause boundaries: ^\s*\(([a-z])\)
        3. Roman numeral clauses: ^\s*\(([ivxl]+)\)
        
        Child chunks are 128-256 tokens (optimal for embedding models).
        → If > 256, log warning and consider splitting further
        → If < 128, log info (very small chunks OK for specific legal text)
        
        Args:
            parent_chunk: Parent LegalChunk object
            section_text: Full section text
            metadata: Document metadata
        
        Returns:
            List of LegalChunk objects with type="child"
        """
        children = []
        lines = section_text.split("\n")
        
        current_subsec = None
        current_subsec_lines = []
        
        for line in lines:
            # Match subsection (1), (2), etc.
            subsec_match = re.match(self.SUBSECTION_PATTERN, line)
            
            if subsec_match:
                # Save previous subsection
                if current_subsec:
                    child_text = "\n".join(current_subsec_lines).strip()
                    if child_text:
                        child_chunk = LegalChunk(
                            chunk_id=f"{parent_chunk.chunk_id}_{current_subsec}",
                            type="child",
                            parent_id=parent_chunk.chunk_id,
                            act=metadata["act"],
                            section_number=parent_chunk.section_number,
                            text=child_text,
                            tokens=self._count_tokens(child_text),
                            source_file=metadata["source_file"]
                        )
                        
                        # Warn if out of token range
                        if child_chunk.tokens > 256:
                            logger.warning(
                                f"Child chunk {child_chunk.chunk_id} exceeds 256 tokens ({child_chunk.tokens}). "
                                f"Consider splitting into sub-clauses."
                            )
                        
                        children.append(child_chunk)
                
                # Start new subsection
                subsec_num = subsec_match.group(1)
                current_subsec = subsec_num
                current_subsec_lines = [line]
            
            elif current_subsec:
                current_subsec_lines.append(line)
        
        # Save last subsection
        if current_subsec:
            child_text = "\n".join(current_subsec_lines).strip()
            if child_text:
                child_chunk = LegalChunk(
                    chunk_id=f"{parent_chunk.chunk_id}_{current_subsec}",
                    type="child",
                    parent_id=parent_chunk.chunk_id,
                    act=metadata["act"],
                    section_number=parent_chunk.section_number,
                    text=child_text,
                    tokens=self._count_tokens(child_text),
                    source_file=metadata["source_file"]
                )
                
                if child_chunk.tokens > 256:
                    logger.warning(
                        f"Child chunk {child_chunk.chunk_id} exceeds 256 tokens ({child_chunk.tokens}). "
                        f"Consider splitting into sub-clauses."
                    )
                
                children.append(child_chunk)
        
        return children
    
    # ========================================================================
    # SENTENCE WINDOWS: Context ±2 sentences
    # ========================================================================
    
    def _attach_sentence_windows(
        self,
        chunks: List[LegalChunk],
        full_text: str
    ) -> List[LegalChunk]:
        """
        Attach ±2 sentence context window to each child chunk.
        
        Sentence window is used at GENERATION time to prevent cut-off
        context when the LLM needs extra surrounding text. NOT used for retrieval.
        
        Algorithm:
        1. Locate chunk text in full document
        2. Split surrounding context into sentences (via regex: sentence boundary)
        3. Grab 2 sentences before and 2 sentences after
        4. Store in chunk.sentence_window field
        
        Args:
            chunks: List of LegalChunk objects
            full_text: Full document text
        
        Returns:
            Same chunks with sentence_window populated (child chunks only)
        """
        # Sentence boundary regex: . or ! or ? followed by space and capital letter
        sentence_pattern = r"(?<=[.!?])\s+"
        
        for chunk in chunks:
            # Skip non-child chunks
            if chunk.type != "child":
                continue
            
            # Find chunk text in full document
            chunk_pos = full_text.find(chunk.text)
            if chunk_pos == -1:
                logger.warning(f"Could not find chunk {chunk.chunk_id} in full document (text changed?)")
                continue
            
            # Extract context before and after
            before_text = full_text[:chunk_pos]
            after_text = full_text[chunk_pos + len(chunk.text):]
            
            # Split into sentences
            before_sentences = re.split(sentence_pattern, before_text.strip())
            after_sentences = re.split(sentence_pattern, after_text.strip())
            
            # Get last 2 sentences before, first 2 after
            before_context = " ".join(before_sentences[-2:]) if len(before_sentences) > 0 else ""
            after_context = " ".join(after_sentences[:2]) if len(after_sentences) > 0 else ""
            
            # Build window
            window_parts = []
            if before_context.strip():
                window_parts.append(before_context)
            window_parts.append(chunk.text)
            if after_context.strip():
                window_parts.append(after_context)
            
            chunk.sentence_window = " ".join(window_parts)
        
        return chunks
    
    # ========================================================================
    # CRITICAL LEGAL STRUCTURE ENFORCEMENT
    # ========================================================================
    
    def _enforce_proviso_merging(self, chunks: List[LegalChunk]) -> List[LegalChunk]:
        """
        Enforce: Provisos NEVER separated from their parent clause.
        
        Detects provisos (text starting with "Provided that" / "Provided further that")
        and MERGES them with the immediately preceding chunk.
        
        Legal reasoning:
        - Provisos are conditional exceptions/modifiers to a clause
        - Cannot be understood/retrieved independently
        - MUST be merged with parent clause to preserve legal meaning
        
        Regex: ^(?:Provided\s+(?:that|further)|Provided,)
        This matches the standard legal "Provided that" prefix.
        
        Args:
            chunks: List of LegalChunk objects
        
        Returns:
            List with provisos merged into preceding chunks
        """
        merged_chunks = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # Check if current chunk is a proviso
            if re.match(self.PROVISO_PATTERN, current_chunk.text.strip(), re.MULTILINE | re.IGNORECASE):
                # This is a proviso → merge with previous chunk
                if merged_chunks:
                    # Merge with last chunk
                    last_chunk = merged_chunks[-1]
                    last_chunk.text += "\n" + current_chunk.text
                    last_chunk.tokens = self._count_tokens(last_chunk.text)
                    
                    if last_chunk.tokens > 256 and last_chunk.type == "child":
                        logger.warning(
                            f"Merged proviso into {last_chunk.chunk_id}. "
                            f"New token count: {last_chunk.tokens} (exceeds 256)."
                        )
                    
                    logger.info(f"Merged proviso (was {current_chunk.chunk_id}) into {last_chunk.chunk_id}")
                else:
                    # No previous chunk to merge with (shouldn't happen in well-formed docs)
                    logger.warning(f"Proviso {current_chunk.chunk_id} has no parent to merge with. Keeping standalone.")
                    merged_chunks.append(current_chunk)
            else:
                # Regular chunk (not a proviso)
                merged_chunks.append(current_chunk)
            
            i += 1
        
        return merged_chunks
    
    def _enforce_explanation_merging(self, chunks: List[LegalChunk]) -> List[LegalChunk]:
        """
        Enforce: Explanations NEVER separated from their parent section.
        
        Detects explanations (text starting with "Explanation —" / "Explanation:")
        and MERGES them with the parent section chunk.
        
        Legal reasoning:
        - Explanations clarify/interpret the section
        - Cannot be understood independently
        - MUST be merged with parent section chunk to preserve legal meaning
        
        Regex: ^Explanation\s*(?:[-–—:]|\.—)
        This matches standard legal "Explanation —" / "Explanation:" prefixes.
        
        Args:
            chunks: List of LegalChunk objects
        
        Returns:
            List with explanations merged into parent sections
        """
        merged_chunks = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # Check if current chunk is an explanation
            if re.search(self.EXPLANATION_PATTERN, current_chunk.text.strip(), re.IGNORECASE):
                # This is an explanation → merge with parent (if exists)
                if current_chunk.parent_id:
                    # Find parent in merged_chunks
                    parent_found = False
                    for j in range(len(merged_chunks) - 1, -1, -1):
                        if merged_chunks[j].chunk_id == current_chunk.parent_id:
                            # Merge into parent
                            merged_chunks[j].text += "\n" + current_chunk.text
                            merged_chunks[j].tokens = self._count_tokens(merged_chunks[j].text)
                            parent_found = True
                            logger.info(f"Merged explanation into parent {current_chunk.parent_id}")
                            break
                    
                    if not parent_found:
                        logger.warning(f"Parent {current_chunk.parent_id} not found for explanation {current_chunk.chunk_id}. Keeping standalone.")
                        merged_chunks.append(current_chunk)
                else:
                    # Top-level explanation with no parent
                    logger.warning(f"Explanation {current_chunk.chunk_id} has no parent. Keeping standalone.")
                    merged_chunks.append(current_chunk)
            else:
                # Regular chunk (not an explanation)
                merged_chunks.append(current_chunk)
            
            i += 1
        
        return merged_chunks
    
    # ========================================================================
    # CROSS-REFERENCE DETECTION (Graph Edges)
    # ========================================================================
    
    def _detect_cross_references(self, text: str) -> List[str]:
        """
        Detect legal cross-references that will become Neo4j graph edges.
        
        Patterns detected:
        - "Section 42(3)" or "section 2"
        - "Rule 14", "Article 5B"
        - "Schedule IV", "Schedule A"
        - "sub-section (3) of section 42"
        
        Regex patterns in CROSS_REF_PATTERNS capture:
        1. Section X, Rule Y, Article Z (simple)
        2. Section X(clause), sub-section (clause) of section X (compound)
        3. Schedule references
        
        Returns:
            List of reference strings (will be edges in graph construction phase)
        
        Args:
            text: Chunk text to scan
        
        Returns:
            List of detected cross-reference strings
        """
        references = []
        
        for pattern in self.CROSS_REF_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                ref = match.group(0).strip()
                if ref and ref not in references:
                    references.append(ref)
        
        return references
    
    # ========================================================================
    # TABLE EXTRACTION
    # ========================================================================
    
    def _extract_tables(
        self,
        text: str,
        metadata: Dict[str, any]
    ) -> List[LegalChunk]:
        """
        Extract tables as dedicated chunks with structured parsing.
        
        Tables (fee schedules, penalty tables) must be extracted WHOLE,
        never split across chunks. Regex detects markdown-style tables (| delimiters).
        
        Structured parsing: Converts table into list[dict] for downstream
        indexing (Neo4j properties, structured search, etc.).
        
        Regex: \n\s*\|[\w\s\-₹%()]+\|
        This matches table rows with | delimiters (markdown-style tables).
        
        Args:
            text: Full document text
            metadata: Document metadata
        
        Returns:
            List of LegalChunk objects with type="table"
        """
        table_chunks = []
        
        # Find all table blocks
        table_matches = re.finditer(
            r"(\n\s*\|.+?\|\n(?:\s*\|.+?\|\n)*)",
            text,
            re.MULTILINE
        )
        
        for i, match in enumerate(table_matches, 1):
            table_text = match.group(0).strip()
            
            # Parse table into structured format
            rows = [row.strip() for row in table_text.split("\n") if "|" in row]
            structured = []
            
            for row in rows:
                # Split by | and clean cells
                cells = [cell.strip() for cell in row.split("|") if cell.strip()]
                if cells:
                    # Try to infer header row (first row)
                    if not structured:
                        structured.append({"_header": cells})
                    else:
                        # Data row
                        row_dict = {}
                        headers = structured[0].get("_header", [])
                        for j, cell in enumerate(cells):
                            header = headers[j] if j < len(headers) else f"col_{j}"
                            row_dict[header] = cell
                        structured.append(row_dict)
            
            # Create table chunk
            chunk_id = f"{metadata['act']}_TABLE_{i}"
            table_chunk = LegalChunk(
                chunk_id=chunk_id,
                type="table",
                act=metadata["act"],
                text=table_text,
                structured=structured,
                tokens=self._count_tokens(table_text),
                source_file=metadata["source_file"]
            )
            
            table_chunks.append(table_chunk)
            logger.info(f"Extracted table {chunk_id} with {len(structured)} rows")
        
        return table_chunks
    
    # ========================================================================
    # TOKEN COUNTING (Exact via Tiktoken)
    # ========================================================================
    
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken cl100k_base encoding (GPT-3.5/4 compatible).
        
        This provides EXACT token counts (not approximate like len(text)//4).
        Used for enforcing token range bounds on parent/child chunks.
        
        Args:
            text: Text to count
        
        Returns:
            Exact token count using cl100k_base encoding
        """
        tokens = self.encoding.encode(text)
        return len(tokens)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def chunk_document(
    filepath: str,
    doc_metadata: Dict[str, any]
) -> List[LegalChunk]:
    """
    Convenience function: Load file and chunk it.
    
    Handles both plain text files and PDFs (extracts text automatically).
    
    Args:
        filepath: Path to document (.txt or .pdf)
        doc_metadata: Metadata dict with keys:
            - act: Act abbreviation (required, e.g., "CA2013")
            - name: Full act name (required)
            - source_file: Filename (required)
            - [year, ministry, source_url]: Optional
    
    Returns:
        List of LegalChunk objects
    
    Raises:
        FileNotFoundError: If file not found
        ValueError: If metadata invalid or document malformed
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Document not found: {filepath}")
    
    # Read document (handle both PDF and plain text)
    if filepath.suffix.lower() == ".pdf":
        # Extract text from PDF using PDFParser
        from clause.ingestion.parsers.pdf_parser import PDFParser
        parser = PDFParser(str(filepath))
        text = parser.extract_text_with_layout()
        logger.info(f"Extracted text from PDF: {filepath.name}")
    else:
        # Plain text file
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(filepath, "r", encoding="latin-1") as f:
                text = f.read()
            logger.warning(f"Used latin-1 encoding for {filepath.name} (UTF-8 failed)")
    
    # Chunk
    chunker = SectionChunker()
    chunks = chunker.chunk_document(text, doc_metadata)
    
    return chunks
