"""
Special Elements Extractor - Extract definitions, penalties, cross-references, etc.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SpecialElement:
    """Special element (definition, penalty, etc.)"""
    element_id: str
    element_type: str  # definition, penalty, threshold, cross_reference
    text: str
    section_reference: str
    metadata: Dict


class SpecialElementsExtractor:
    """Extract and structure special legal elements"""
    
    # Patterns for different elements
    DEFINITION_PATTERN = r"['\"]([^'\"]+?)['\"]\s+(?:means|includes|defined as|shall include|shall mean)\s+(.+?)(?:\.\s|;\s|\n|$)"
    PENALTY_PATTERN = r"(?:punishable|fine|imprisonment|penalty)\s+(?:which\s+)?(?:shall\s+)?(?:be|not\s+be)?.*?(?:₹|Rs|rupees|years).*?(?:\.|,|\n)"
    THRESHOLD_PATTERN = r"(?:turnover|shareholding|number of|minimum|maximum)\s+(?:not\s+exceeding|exceeding|of|is)\s+(₹[\d\s,]+\s+(?:crore|lakh|rupees)?|[\d\s,]+\s+(?:crore|lakh|percent|%|days)?)"
    CROSS_REFERENCE_PATTERN = r"(?:see|refer|as\s+per|in\s+accordance\s+with|under|pursuant\s+to)\s+(?:Section|Rule|Schedule|Article)\s+(\d+[A-Z]*)"
    EXCEPTION_PATTERN = r"(?:except|notwithstanding|provided|proviso)\s+(?:that\s+)?(.+?)(?:\.|;|\n)"
    
    def __init__(self, document_name: str, act_name: str):
        self.document_name = document_name
        self.act_name = act_name
        self.elements: List[SpecialElement] = []
        self.element_counter = 0
    
    def extract_all(self, text: str) -> Dict[str, List[SpecialElement]]:
        """
        Extract all special elements from text
        
        Args:
            text: Full document text
            
        Returns:
            Dict grouped by element type
        """
        logger.info(f"Extracting special elements from {self.document_name}")
        
        all_elements = {
            "definitions": self._extract_definitions(text),
            "penalties": self._extract_penalties(text),
            "thresholds": self._extract_thresholds(text),
            "cross_references": self._extract_cross_references(text),
            "exceptions": self._extract_exceptions(text)
        }
        
        for elem_type, elements in all_elements.items():
            logger.info(f"Found {len(elements)} {elem_type}")
        
        return all_elements
    
    def _extract_definitions(self, text: str) -> List[SpecialElement]:
        """Extract legal definitions"""
        definitions = []
        
        # Pattern 1: Quoted terms with "means"
        for match in re.finditer(self.DEFINITION_PATTERN, text, re.IGNORECASE | re.DOTALL):
            term = match.group(1)
            definition = match.group(2)
            
            elem_id = f"definition_{term.lower().replace(' ', '_')}"
            
            element = SpecialElement(
                element_id=elem_id,
                element_type="definition",
                text=f'"{term}" means {definition}',
                section_reference=self._find_section_context(text, match.start()),
                metadata={
                    "defined_term": term,
                    "definition_text": definition.strip(),
                    "match_confidence": 0.9
                }
            )
            definitions.append(element)
        
        # Pattern 2: "Section X: Definition of Y"
        section_definition_pattern = r"Section\s+(\d+[A-Z]*)\s*:\s*(.+?)\s+[Dd]efinition\s+of\s+(.+?)(?:\n|$)"
        
        for match in re.finditer(section_definition_pattern, text):
            section = match.group(1)
            heading = match.group(2)
            term = match.group(3)
            
            elem_id = f"section_{section}_definition_{term.lower().replace(' ', '_')}"
            
            element = SpecialElement(
                element_id=elem_id,
                element_type="definition",
                text=f"Definition in Section {section}: {term}",
                section_reference=f"Section {section}",
                metadata={
                    "defined_term": term,
                    "defined_in_section": section,
                    "section_heading": heading
                }
            )
            definitions.append(element)
        
        return definitions
    
    def _extract_penalties(self, text: str) -> List[SpecialElement]:
        """Extract penalty provisions"""
        penalties = []
        
        # Find all penalty-related sentences
        for match in re.finditer(self.PENALTY_PATTERN, text, re.IGNORECASE | re.DOTALL):
            penalty_text = match.group(0)
            section_ref = self._find_section_context(text, match.start())
            
            elem_id = f"penalty_{len(penalties)}"
            
            # Parse penalty amounts
            amount_match = re.search(r"₹\s*([\d,]+)\s*(?:crore|lakh|rupees)?.*?₹\s*([\d,]+)", penalty_text)
            min_amt, max_amt = None, None
            
            if amount_match:
                min_amt = amount_match.group(1).replace(",", "")
                max_amt = amount_match.group(2).replace(",", "")
            
            # Parse imprisonment
            imprisonment_match = re.search(r"imprisonment\s+(?:for\s+)?(?:a\s+)?(?:term\s+)?(?:of\s+)?(\d+)\s+(?:year|month|day)", penalty_text)
            imprisonment = imprisonment_match.group(1) if imprisonment_match else None
            
            element = SpecialElement(
                element_id=elem_id,
                element_type="penalty",
                text=penalty_text.strip(),
                section_reference=section_ref,
                metadata={
                    "penalty_min_amount": min_amt,
                    "penalty_max_amount": max_amt,
                    "imprisonment_months": imprisonment,
                    "currency": "INR"
                }
            )
            penalties.append(element)
        
        return penalties
    
    def _extract_thresholds(self, text: str) -> List[SpecialElement]:
        """Extract thresholds (turnover, shareholding, etc.)"""
        thresholds = []
        
        for match in re.finditer(self.THRESHOLD_PATTERN, text, re.IGNORECASE):
            threshold_text = match.group(0)
            value = match.group(1)
            section_ref = self._find_section_context(text, match.start())
            
            elem_id = f"threshold_{len(thresholds)}"
            
            # Parse the threshold type and value
            threshold_type = "unknown"
            if "turnover" in threshold_text.lower():
                threshold_type = "turnover"
            elif "shareholding" in threshold_text.lower():
                threshold_type = "shareholding"
            elif "number of" in threshold_text.lower():
                threshold_type = "count"
            
            element = SpecialElement(
                element_id=elem_id,
                element_type="threshold",
                text=threshold_text.strip(),
                section_reference=section_ref,
                metadata={
                    "threshold_type": threshold_type,
                    "threshold_value": value,
                    "applies_to": self._extract_applies_to(threshold_text)
                }
            )
            thresholds.append(element)
        
        return thresholds
    
    def _extract_cross_references(self, text: str) -> List[SpecialElement]:
        """Extract cross-references to other sections"""
        cross_refs = []
        
        for match in re.finditer(self.CROSS_REFERENCE_PATTERN, text, re.IGNORECASE):
            reference_text = match.group(0)
            referenced_section = match.group(1)
            section_ref = self._find_section_context(text, match.start())
            
            elem_id = f"cross_ref_{len(cross_refs)}"
            
            element = SpecialElement(
                element_id=elem_id,
                element_type="cross_reference",
                text=reference_text.strip(),
                section_reference=section_ref,
                metadata={
                    "referenced_section": referenced_section,
                    "reference_type": self._classify_reference(reference_text),
                    "from_section": section_ref
                }
            )
            cross_refs.append(element)
        
        return cross_refs
    
    def _extract_exceptions(self, text: str) -> List[SpecialElement]:
        """Extract exceptions and provisos"""
        exceptions = []
        
        for match in re.finditer(self.EXCEPTION_PATTERN, text, re.IGNORECASE):
            exception_text = match.group(0)
            condition = match.group(1) if match.lastindex >= 1 else ""
            section_ref = self._find_section_context(text, match.start())
            
            elem_id = f"exception_{len(exceptions)}"
            
            element = SpecialElement(
                element_id=elem_id,
                element_type="exception",
                text=exception_text.strip(),
                section_reference=section_ref,
                metadata={
                    "exception_type": "proviso" if "proviso" in exception_text.lower() else "exception",
                    "condition": condition.strip(),
                    "applies_to_section": section_ref
                }
            )
            exceptions.append(element)
        
        return exceptions
    
    @staticmethod
    def _find_section_context(text: str, position: int, context_chars: int = 200) -> str:
        """Find the nearest section reference before given position"""
        # Look backwards for section reference
        context_start = max(0, position - context_chars)
        context = text[context_start:position]
        
        section_match = re.search(r"Section\s+(\d+[A-Z]*)", context)
        if section_match:
            return f"Section {section_match.group(1)}"
        
        return "Unknown"
    
    @staticmethod
    def _classify_reference(text: str) -> str:
        """Classify the type of reference (definition, related_rule, etc.)"""
        text_lower = text.lower()
        
        if "definition" in text_lower or "defined" in text_lower:
            return "definition"
        elif "rule" in text_lower:
            return "related_rule"
        elif "schedule" in text_lower:
            return "related_schedule"
        elif "amended" in text_lower:
            return "amendment"
        else:
            return "cross_reference"
    
    @staticmethod
    def _extract_applies_to(text: str) -> List[str]:
        """Extract entity types this applies to from text"""
        applies_to = []
        
        entity_keywords = {
            "PrivateLimited": ["private", "private limited", "pvt"],
            "PublicCompany": ["public", "public limited", "public company"],
            "OPC": ["one person company", "opc", "single director"],
            "LLP": ["llp", "limited liability partnership"],
            "Partnership": ["partnership", "partnership firm"],
            "HUF": ["huf", "hindu undivided family"],
            "Government": ["government", "state", "union"]
        }
        
        text_lower = text.lower()
        
        for entity_type, keywords in entity_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                applies_to.append(entity_type)
        
        return applies_to
