#!/usr/bin/env python
"""
Quick-start script for the Clause ingestion pipeline
Run from project root: python run_pipeline.py
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from clause.ingestion.pipeline import IngestionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    
    print("\n" + "="*70)
    print("  CLAUSE INGESTION PIPELINE - Quick Start")
    print("="*70 + "\n")
    
    # Check if data/raw exists
    data_raw = Path("data/raw")
    if not data_raw.exists():
        print("❌ Error: data/raw directory not found!")
        print("   Please ensure PDFs are in data/raw/")
        sys.exit(1)
    
    # Count PDFs
    pdf_count = len(list(data_raw.glob("**/*.pdf")))
    print(f"✓ Found {pdf_count} PDF files in data/raw/")
    
    if pdf_count == 0:
        print("⚠️  No PDFs found! Please add documents to data/raw/")
        sys.exit(1)
    
    print("\n" + "-"*70)
    print("Starting pipeline (this may take 5-15 minutes for full corpus)...")
    print("-"*70 + "\n")
    
    try:
        # Initialize and run pipeline
        pipeline = IngestionPipeline(data_root="data")
        pipeline.run()
        
        print("\n" + "="*70)
        print("  ✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nNext steps:")
        print("1. Review chunks: ls -la data/processed/chunks/ | head")
        print("2. Check metadata: cat data/processed/entities/all_chunks_metadata.json | head")
        print("3. Start Docker: docker-compose up -d")
        print("4. Index chunks in Qdrant")
        print("5. Import relationships to Neo4j")
        print("="*70 + "\n")
        
        return 0
    
    except Exception as e:
        print("\n" + "="*70)
        print(f"  ❌ PIPELINE FAILED: {e}")
        print("="*70 + "\n")
        logger.exception("Pipeline error:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
