"""
PDF Parser - Extract text and structure from PDF files
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

import pdfplumber

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.documents.elements import Title, Paragraph, Table, NarrativeText
    HAS_UNSTRUCTURED = True
except ImportError:
    HAS_UNSTRUCTURED = False
    logger_tmp = logging.getLogger(__name__)
    logger_tmp.warning("unstructured not installed, will use pdfplumber only")

logger = logging.getLogger(__name__)


class PDFParser:
    """Extract text and structure from PDFs using pdfplumber + unstructured"""
    
    def __init__(self, filepath: str):
        """
        Initialize parser with PDF file
        
        Args:
            filepath: Path to PDF file
        """
        self.filepath = filepath
        self.filename = Path(filepath).stem
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"PDF not found: {filepath}")
    
    def extract_text_with_layout(self) -> str:
        """
        Extract text preserving approximate layout using pdfplumber
        
        Returns:
            Full text with section breaks
        """
        try:
            full_text = []
            with pdfplumber.open(self.filepath) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        full_text.append(f"\n--- PAGE {page_num} ---\n{text}")
            
            return "\n".join(full_text)
        
        except Exception as e:
            logger.error(f"Error extracting text from {self.filepath}: {e}")
            raise
    
    def extract_tables(self) -> List[Dict]:
        """
        Extract tables from PDF using pdfplumber
        
        Returns:
            List of table dicts with page number and data
        """
        tables = []
        try:
            with pdfplumber.open(self.filepath) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    
                    if page_tables:
                        for table_idx, table in enumerate(page_tables):
                            tables.append({
                                "page": page_num,
                                "table_index": table_idx,
                                "data": table,
                                "markdown": self._table_to_markdown(table)
                            })
            
            logger.info(f"Extracted {len(tables)} tables from {self.filename}")
            return tables
        
        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")
            return []
    
    @staticmethod
    def _table_to_markdown(table: List[List[str]]) -> str:
        """Convert table to markdown format"""
        if not table:
            return ""
        
        lines = []
        # Header
        lines.append("| " + " | ".join(str(cell) for cell in table[0]) + " |")
        # Separator
        lines.append("|" + "|".join(["---"] * len(table[0])) + "|")
        # Rows
        for row in table[1:]:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        
        return "\n".join(lines)
    
    def detect_structure(self) -> Dict[str, List]:
        """
        Detect document structure (sections, headings, etc.) using unstructured
        
        Returns:
            Dict with detected elements by type
        """
        if not HAS_UNSTRUCTURED:
            logger.info("unstructured not available, skipping structure detection")
            return {
                "titles": [],
                "paragraphs": [],
                "tables": [],
                "other": []
            }
        
        try:
            elements = partition_pdf(self.filepath)
            
            structure = {
                "titles": [],
                "paragraphs": [],
                "tables": [],
                "other": []
            }
            
            for elem in elements:
                if isinstance(elem, Title):
                    structure["titles"].append(str(elem))
                elif isinstance(elem, Paragraph) or isinstance(elem, NarrativeText):
                    structure["paragraphs"].append(str(elem))
                elif isinstance(elem, Table):
                    structure["tables"].append(str(elem))
                else:
                    structure["other"].append(str(elem))
            
            logger.info(f"Detected structure: {len(structure['titles'])} titles, "
                       f"{len(structure['paragraphs'])} paragraphs, "
                       f"{len(structure['tables'])} tables")
            
            return structure
        
        except Exception as e:
            logger.warning(f"Error detecting structure: {e}")
            return {
                "titles": [],
                "paragraphs": [],
                "tables": [],
                "other": []
            }
    
    def parse(self) -> Dict[str, any]:
        """
        Full parse: extract text, detect structure, extract tables
        
        Returns:
            Dict with all extracted data
        """
        logger.info(f"Parsing PDF: {self.filename}")
        
        return {
            "filename": self.filename,
            "filepath": self.filepath,
            "text": self.extract_text_with_layout(),
            "structure": self.detect_structure(),
            "tables": self.extract_tables()
        }
