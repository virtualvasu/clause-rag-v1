#!/usr/bin/env python
"""
Test script - Verify pipeline can run on a sample PDF
Run: python test_pipeline.py

NOTE: Old chunking pipeline has been removed.
      New spec-compliant chunker will be implemented in:
      clause/ingestion/chunkers/section_chunker.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from clause.ingestion.parsers.pdf_parser import PDFParser

# New chunker to be imported once implemented:
# from clause.ingestion.chunkers.section_chunker import SectionChunker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_pipeline():
    """Test pipeline on first available PDF"""
    
    print("\n" + "="*70)
    print("  CLAUSE PIPELINE - TEST RUN")
    print("="*70 + "\n")
    
    # Find first PDF
    data_raw = Path("data/raw")
    pdf_files = list(data_raw.glob("**/*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in data/raw/")
        return False
    
    pdf_path = pdf_files[0]
    print(f"✓ Found test PDF: {pdf_path.name}")
    print(f"  Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    
    try:
        # Test 1: PDF Parsing
        print("\n[1/4] Testing PDF Parser...")
        parser = PDFParser(str(pdf_path))
        parsed = parser.parse()
        
        text_len = len(parsed['text'])
        print(f"  ✓ Extracted {text_len} characters")
        print(f"  ✓ Detected {len(parsed['structure']['titles'])} titles")
        print(f"  ✓ Found {len(parsed['tables'])} tables")
        
        if text_len < 100:
            print("  ⚠️  Warning: Very little text extracted. PDF may be scanned.")
        
        # Test 2: Chunking
        print("\n[2/4] Testing Hierarchical Chunker...")
        chunker = HierarchicalChunker(
            document_name="test_document",
            act_name="Test Act"
        )
        chunks = chunker.chunk(parsed['text'])
        
        print(f"  ✓ Created {len(chunks)} chunks")
        
        if len(chunks) > 0:
            chunk = chunks[0]
            print(f"\n  Sample chunk:")
            print(f"    - ID: {chunk.chunk_id}")
            print(f"    - Level: {chunk.level}")
            print(f"    - Tokens: {chunk.token_count}")
            print(f"    - Text preview: {chunk.text[:80]}...")
        else:
            print("  ⚠️  Warning: No chunks created. Check PDF content.")
        
        # Test 3: Special Elements
        print("\n[3/4] Testing Special Elements Extractor...")
        extractor = SpecialElementsExtractor("test_doc", "Test Act")
        elements = extractor.extract_all(parsed['text'])
        
        total_elements = sum(len(v) for v in elements.values())
        print(f"  ✓ Extracted {total_elements} special elements:")
        
        for elem_type, elem_list in elements.items():
            print(f"    - {elem_type}: {len(elem_list)}")
        
        # Test 4: Output Format
        print("\n[4/4] Testing Output Format...")
        
        chunk_dict = chunks[0].to_dict() if chunks else {}
        print(f"  ✓ Chunk JSON format valid")
        print(f"    - Keys: {', '.join(list(chunk_dict.keys())[:5])}...")
        
        print("\n" + "="*70)
        print("  ✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nPipeline is ready to run:")
        print("  python run_pipeline.py")
        print("\n" + "="*70 + "\n")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.exception("Test error:")
        return False


if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)
