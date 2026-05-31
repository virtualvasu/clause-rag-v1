"""
Hierarchical Chunker - Split documents into multi-level chunks
Implements the 3-level chunking strategy:
- Level 1: Full Section (Parent Chunk)
- Level 2: Subsection/Proviso (Child Chunk)  
- Level 3: Clause/Definition (Granular Chunk)
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Chunk data structure"""
    chunk_id: str
    text: str
    level: str  # "section", "subsection", "clause"
    document: str
    act_name: str
    section: Optional[str] = None
    subsection: Optional[str] = None
    clause: Optional[str] = None
    heading: Optional[str] = None
    parent_chunk_id: Optional[str] = None
    children_ids: List[str] = None
    token_count: int = 0
    full_path: str = ""
    type: str = "standard"  # standard, definition, penalty, table, amendment
    applies_to: List[str] = None  # e.g. ["PrivateLimited", "PublicCompany"]
    condition_tags: List[str] = None  # e.g. ["turnover > 50Cr", "foreign_directors"]
    cross_references: List[str] = None
    effective_date: Optional[str] = None
    amendments: List[str] = None
    source_page: int = 0
    
    def __post_init__(self):
        if self.children_ids is None:
            self.children_ids = []
        if self.applies_to is None:
            self.applies_to = []
        if self.condition_tags is None:
            self.condition_tags = []
        if self.cross_references is None:
            self.cross_references = []
        if self.amendments is None:
            self.amendments = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary, exclude None values"""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None and v != [] and v != ""}


class HierarchicalChunker:
    """
    Split legal documents hierarchically while preserving structure
    """
    
    # Regex patterns for legal structure
    SECTION_PATTERN = r"^(Section|Rule|Article)\s+(\d+[A-Z]*)"
    SUBSECTION_PATTERN = r"^\s*\((\d+)\)\s"  # (1), (2), (3)
    CLAUSE_PATTERN = r"^\s*\(([a-z])\)\s"     # (a), (b), (c)
    CLAUSE_ROMAN = r"^\s*\(([ivx]+)\)\s"      # (i), (ii), (iii)
    DEFINITION_PATTERN = r"(?:means|includes|defined as|shall include)[\s:\"]"
    PENALTY_PATTERN = r"(?:punishable|fine|imprisonment|penalty)"
    PROVISO_PATTERN = r"^\s*Provided\s+(?:that|further)?\s*"
    EXPLANATION_PATTERN = r"^\s*Explanation[\s:-]"
    
    def __init__(self, document_name: str, act_name: str, effective_date: str = None):
        """
        Initialize chunker
        
        Args:
            document_name: Name of document (e.g., "Companies_Act_2013")
            act_name: Full act name (e.g., "Companies Act 2013")
            effective_date: Effective date in YYYY-MM-DD format
        """
        self.document_name = document_name
        self.act_name = act_name
        self.effective_date = effective_date or "2013-09-12"
        self.chunks: List[Chunk] = []
        self.chunk_counter = 0
    
    def chunk(self, text: str) -> List[Chunk]:
        """
        Main chunking method - orchestrates the hierarchical splitting
        
        Args:
            text: Full document text
            
        Returns:
            List of Chunk objects
        """
        logger.info(f"Starting hierarchical chunking for {self.document_name}")
        
        # Split into sections (Level 1 - Parent chunks)
        sections = self._extract_sections(text)
        logger.info(f"Found {len(sections)} sections")
        
        for section_data in sections:
            section_num = section_data["section"]
            section_text = section_data["text"]
            section_heading = section_data["heading"]
            
            # Create parent chunk (full section)
            parent_chunk = self._create_section_chunk(
                section_num=section_num,
                text=section_text,
                heading=section_heading
            )
            self.chunks.append(parent_chunk)
            
            # Split section into subsections (Level 2 - Child chunks)
            subsections = self._extract_subsections(section_text)
            
            if subsections:
                for subsec_data in subsections:
                    subsec_num = subsec_data["number"]
                    subsec_text = subsec_data["text"]
                    
                    # Create child chunk (subsection/proviso)
                    child_chunk = self._create_subsection_chunk(
                        section_num=section_num,
                        subsection_num=subsec_num,
                        text=subsec_text,
                        parent_id=parent_chunk.chunk_id,
                        section_heading=section_heading
                    )
                    self.chunks.append(child_chunk)
                    parent_chunk.children_ids.append(child_chunk.chunk_id)
                    
                    # Split subsection into clauses (Level 3 - Granular chunks)
                    clauses = self._extract_clauses(subsec_text)
                    
                    if clauses:
                        for clause_data in clauses:
                            clause_num = clause_data["number"]
                            clause_text = clause_data["text"]
                            
                            # Create granular chunk (clause)
                            granular_chunk = self._create_clause_chunk(
                                section_num=section_num,
                                subsection_num=subsec_num,
                                clause_num=clause_num,
                                text=clause_text,
                                parent_id=child_chunk.chunk_id,
                                section_heading=section_heading
                            )
                            self.chunks.append(granular_chunk)
                            child_chunk.children_ids.append(granular_chunk.chunk_id)
        
        logger.info(f"Created {len(self.chunks)} total chunks")
        return self.chunks
    
    def _extract_sections(self, text: str) -> List[Dict]:
        """Extract sections from text"""
        sections = []
        lines = text.split("\n")
        
        current_section = None
        current_section_lines = []
        
        for line in lines:
            match = re.match(self.SECTION_PATTERN, line)
            
            if match:
                # Save previous section
                if current_section:
                    sections.append({
                        "section": current_section["number"],
                        "heading": current_section.get("heading", ""),
                        "text": "\n".join(current_section_lines).strip()
                    })
                
                # Start new section
                section_num = match.group(2)
                current_section = {
                    "number": section_num,
                    "heading": line.strip()
                }
                current_section_lines = [line]
            
            elif current_section:
                current_section_lines.append(line)
        
        # Save last section
        if current_section:
            sections.append({
                "section": current_section["number"],
                "heading": current_section.get("heading", ""),
                "text": "\n".join(current_section_lines).strip()
            })
        
        return sections
    
    def _extract_subsections(self, section_text: str) -> List[Dict]:
        """Extract subsections from section text"""
        subsections = []
        lines = section_text.split("\n")
        
        current_subsec = None
        current_subsec_lines = []
        
        for i, line in enumerate(lines):
            # Skip the section heading (first line)
            if i == 0:
                continue
            
            # Check for subsection start: (1), (2), etc.
            subsec_match = re.match(self.SUBSECTION_PATTERN, line)
            
            # Also check for Proviso
            proviso_match = re.match(self.PROVISO_PATTERN, line)
            
            if subsec_match or proviso_match:
                # Save previous subsection
                if current_subsec:
                    subsections.append({
                        "number": current_subsec,
                        "text": "\n".join(current_subsec_lines).strip()
                    })
                
                # Start new subsection
                if subsec_match:
                    current_subsec = subsec_match.group(1)
                else:
                    current_subsec = "proviso"  # Special marker for provisos
                
                current_subsec_lines = [line]
            
            elif current_subsec:
                current_subsec_lines.append(line)
        
        # Save last subsection
        if current_subsec:
            subsections.append({
                "number": current_subsec,
                "text": "\n".join(current_subsec_lines).strip()
            })
        
        return subsections
    
    def _extract_clauses(self, subsection_text: str) -> List[Dict]:
        """Extract clauses from subsection text"""
        clauses = []
        lines = subsection_text.split("\n")
        
        current_clause = None
        current_clause_lines = []
        
        for i, line in enumerate(lines):
            # Skip the first line (subsection header)
            if i == 0:
                continue
            
            # Check for clause: (a), (b), (c) or (i), (ii), (iii)
            clause_match = re.match(self.CLAUSE_PATTERN, line)
            roman_match = re.match(self.CLAUSE_ROMAN, line)
            
            if clause_match or roman_match:
                # Save previous clause
                if current_clause:
                    clauses.append({
                        "number": current_clause,
                        "text": "\n".join(current_clause_lines).strip()
                    })
                
                # Start new clause
                current_clause = clause_match.group(1) if clause_match else roman_match.group(1)
                current_clause_lines = [line]
            
            elif current_clause:
                current_clause_lines.append(line)
        
        # Save last clause
        if current_clause:
            clauses.append({
                "number": current_clause,
                "text": "\n".join(current_clause_lines).strip()
            })
        
        return clauses
    
    def _create_section_chunk(self, section_num: str, text: str, heading: str) -> Chunk:
        """Create a Level 1 (full section) chunk"""
        chunk_id = f"section_{section_num}_full"
        
        chunk = Chunk(
            chunk_id=chunk_id,
            text=text,
            level="section",
            document=self.document_name,
            act_name=self.act_name,
            section=section_num,
            heading=heading,
            token_count=self._count_tokens(text),
            full_path=f"{self.act_name} > Section {section_num}",
            effective_date=self.effective_date
        )
        
        return chunk
    
    def _create_subsection_chunk(
        self, 
        section_num: str, 
        subsection_num: str, 
        text: str,
        parent_id: str,
        section_heading: str
    ) -> Chunk:
        """Create a Level 2 (subsection/proviso) chunk"""
        chunk_id = f"section_{section_num}_subsection_{subsection_num}"
        
        chunk = Chunk(
            chunk_id=chunk_id,
            text=text,
            level="subsection",
            document=self.document_name,
            act_name=self.act_name,
            section=section_num,
            subsection=subsection_num,
            heading=section_heading,
            parent_chunk_id=parent_id,
            token_count=self._count_tokens(text),
            full_path=f"{self.act_name} > Section {section_num} > Subsection ({subsection_num})",
            effective_date=self.effective_date
        )
        
        # Detect type: proviso, explanation, or standard
        if "proviso" in subsection_num.lower():
            chunk.type = "proviso"
        elif re.search(self.EXPLANATION_PATTERN, text, re.IGNORECASE):
            chunk.type = "explanation"
        
        return chunk
    
    def _create_clause_chunk(
        self,
        section_num: str,
        subsection_num: str,
        clause_num: str,
        text: str,
        parent_id: str,
        section_heading: str
    ) -> Chunk:
        """Create a Level 3 (clause/definition) chunk"""
        chunk_id = f"section_{section_num}_subsection_{subsection_num}_clause_{clause_num}"
        
        chunk = Chunk(
            chunk_id=chunk_id,
            text=text,
            level="clause",
            document=self.document_name,
            act_name=self.act_name,
            section=section_num,
            subsection=subsection_num,
            clause=clause_num,
            heading=section_heading,
            parent_chunk_id=parent_id,
            token_count=self._count_tokens(text),
            full_path=f"{self.act_name} > Section {section_num} > Subsection ({subsection_num}) > Clause ({clause_num})",
            effective_date=self.effective_date
        )
        
        # Detect chunk type
        if re.search(self.DEFINITION_PATTERN, text, re.IGNORECASE):
            chunk.type = "definition"
        elif re.search(self.PENALTY_PATTERN, text, re.IGNORECASE):
            chunk.type = "penalty"
        
        return chunk
    
    @staticmethod
    def _count_tokens(text: str) -> int:
        """
        Rough token count (approximate)
        Actual count should use tiktoken, but this is good enough for now
        Rule of thumb: ~4 chars per token
        """
        return len(text) // 4
