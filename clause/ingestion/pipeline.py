"""
Main Ingestion Pipeline Orchestrator

Spec-compliant pipeline orchestrating:
1. PDF text extraction via PDFParser
2. 3-layer hierarchical chunking via SectionChunker (spec: chunking.md)
3. Chunk persistence to data/processed/chunks/ (one JSON per chunk)
4. Neo4j relationships CSV generation from parent-child and cross-references
5. Summary report generation

Matches chunking.md specification exactly:
- Layer 1: Document metadata (type="document")
- Layer 2: Parent chunks (type="parent", 512-1024 tokens, one per section)
- Layer 3: Child chunks (type="child", 128-256 tokens, one per sub-section)
- Plus: Sentence windows (±2 sentences), Tables (type="table"), Cross-refs (graph edges)
"""

import os
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from clause.ingestion.chunkers.section_chunker import chunk_document, LegalChunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Main ingestion pipeline orchestrator.
    
    Spec compliance:
    - Accepts documents via document_configs with act, name, source_file metadata
    - Passes metadata to chunk_document() which returns List[LegalChunk]
    - Persists all chunks as individual JSON files to data/processed/chunks/
    - Generates Neo4j relationships.csv from parent-child and cross-reference edges
    - Produces summary report with statistics
    """
    
    def __init__(self, data_root: str = "data"):
        """
        Initialize pipeline with directory structure.
        
        Args:
            data_root: Root data directory (default: "data")
            
        Creates:
            - data/processed/chunks/ (one JSON per LegalChunk)
            - data/processed/graph/ (relationships.csv for Neo4j)
            - data/processed/entities/ (summary.md)
        """
        self.data_root = Path(data_root)
        self.raw_dir = self.data_root / "raw"
        self.processed_dir = self.data_root / "processed"
        self.chunks_dir = self.processed_dir / "chunks"
        self.graph_dir = self.processed_dir / "graph"
        self.entities_dir = self.processed_dir / "entities"
        
        # Create output directories
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        self.entities_dir.mkdir(parents=True, exist_ok=True)
        
        # Document configurations
        # Each entry: key = doc_name, value = {filename, act, name, source_file, subfolder}
        # Passed to chunk_document(filepath, doc_metadata={act, name, source_file})
        self.document_configs = {
            "Companies_Act_2013": {
                "filename": "Companies_Act_2013.pdf",
                "act": "CA2013",
                "name": "Companies Act 2013",
                "source_file": "Companies_Act_2013.pdf",
                "subfolder": "companies_act"
            },
            "Companies_Incorporation_Rules_2014": {
                "filename": "Companies_Incorporation_Rules_2014.pdf",
                "act": "CIR2014",
                "name": "Companies (Incorporation) Rules 2014",
                "source_file": "Companies_Incorporation_Rules_2014.pdf",
                "subfolder": "companies_rules"
            },
            "Companies_Share_Capital_Rules_2014": {
                "filename": "Companies_Share_Capital_Rules_2014.pdf",
                "act": "CSCR2014",
                "name": "Companies (Share Capital) Rules 2014",
                "source_file": "Companies_Share_Capital_Rules_2014.pdf",
                "subfolder": "companies_rules"
            },
            "Companies_Accounts_Rules_2014": {
                "filename": "Companies_Accounts_Rules_2014.pdf",
                "act": "CAR2014",
                "name": "Companies (Accounts) Rules 2014",
                "source_file": "Companies_Accounts_Rules_2014.pdf",
                "subfolder": "companies_rules"
            },
            "Companies_Meetings_Rules_2014": {
                "filename": "Companies_Meetings_Rules_2014.pdf",
                "act": "CMR2014",
                "name": "Companies (Meetings) Rules 2014",
                "source_file": "Companies_Meetings_Rules_2014.pdf",
                "subfolder": "companies_rules"
            },
            "Companies_Directors_Rules_2014": {
                "filename": "Companies_Directors_Rules_2014.pdf",
                "act": "CDR2014",
                "name": "Companies (Directors) Rules 2014",
                "source_file": "Companies_Directors_Rules_2014.pdf",
                "subfolder": "companies_rules"
            },
            "SEBI_ICDR_Regulations_2018": {
                "filename": "SEBI_ICDR_Regulations_2018.pdf",
                "act": "SEBI_ICDR2018",
                "name": "SEBI (ICDR) Regulations 2018",
                "source_file": "SEBI_ICDR_Regulations_2018.pdf",
                "subfolder": "sebi"
            },
            "SEBI_AIF_Regulations_2012": {
                "filename": "SEBI_AIF_Regulations_2012.pdf",
                "act": "SEBI_AIF2012",
                "name": "SEBI (AIF) Regulations 2012",
                "source_file": "SEBI_AIF_Regulations_2012.pdf",
                "subfolder": "sebi"
            },
            "DPIIT_Startup_Recognition_Guidelines": {
                "filename": "DPIIT_Startup_Recognition_Guidelines.pdf",
                "act": "DPIIT_SRG",
                "name": "DPIIT Startup Recognition Guidelines",
                "source_file": "DPIIT_Startup_Recognition_Guidelines.pdf",
                "subfolder": "dpiit"
            },
            "Startup_India_Tax_Exemption_80IAC": {
                "filename": "Startup_India_Tax_Exemption_80IAC.pdf",
                "act": "SITAX_80IAC",
                "name": "Startup India Tax Exemption (Section 80IAC)",
                "source_file": "Startup_India_Tax_Exemption_80IAC.pdf",
                "subfolder": "startup_tax"
            }
        }
        
        # State tracking
        self.all_chunks: List[LegalChunk] = []
        self.processing_stats = {
            "total_documents": 0,
            "successful_documents": 0,
            "failed_documents": 0,
            "total_chunks": 0,
            "documents_by_type": {}  # counts of each chunk type
        }
    
    
    def run(self, documents: Optional[List[str]] = None):
        """
        Run the full ingestion pipeline.
        
        Args:
            documents: List of document config keys to process (None = all)
            
        Execution flow:
            1. For each document:
               a. Load PDF via chunk_document() → List[LegalChunk]
               b. Save each chunk as {chunk_id}.json
               c. Track statistics
            2. Generate relationships.csv from parent-child and cross-ref edges
            3. Generate summary.md report
        """
        logger.info("=" * 70)
        logger.info("CLAUSE INGESTION PIPELINE STARTING")
        logger.info("Spec: context/chunking.md")
        logger.info("=" * 70)
        
        if documents is None:
            documents = list(self.document_configs.keys())
        
        self.processing_stats["total_documents"] = len(documents)
        
        for doc_name in documents:
            try:
                self._process_document(doc_name)
                self.processing_stats["successful_documents"] += 1
            except Exception as e:
                logger.error(f"❌ Failed to process {doc_name}: {str(e)[:100]}", exc_info=True)
                self.processing_stats["failed_documents"] += 1
        
        # Save consolidated outputs
        self._save_relationships_csv()
        self._save_summary_report()
        
        # Print statistics
        self._print_statistics()
    
    def _process_document(self, doc_name: str):
        """
        Process a single document via spec-compliant chunking pipeline.
        
        Steps:
            1. Validate document config and file exists
            2. Call chunk_document(filepath, doc_metadata={act, name, source_file})
            3. Persist each LegalChunk to data/processed/chunks/{chunk_id}.json
            4. Track statistics by chunk type
            
        Args:
            doc_name: Key in self.document_configs
            
        Raises:
            FileNotFoundError: If PDF not found
            ValueError: If chunking fails (returned from SectionChunker)
        """
        config = self.document_configs[doc_name]
        filepath = self.raw_dir / config["subfolder"] / config["filename"]
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Document: {doc_name}")
        logger.info(f"File: {filepath}")
        logger.info(f"={'=' * 70}")
        
        # Validate file exists
        if not filepath.exists():
            raise FileNotFoundError(f"PDF not found: {filepath}")
        
        # Run spec-compliant chunking pipeline
        logger.info("Chunking via SectionChunker...")
        try:
            chunks = chunk_document(
                str(filepath),
                doc_metadata={
                    "act": config["act"],
                    "name": config["name"],
                    "source_file": config["source_file"]
                }
            )
        except Exception as e:
            raise ValueError(f"Chunking failed: {str(e)}")
        
        # Save chunks
        logger.info(f"Saving {len(chunks)} chunks...")
        for chunk in chunks:
            self._save_chunk(chunk)
            self.all_chunks.append(chunk)
        
        # Track statistics by chunk type
        for chunk in chunks:
            if chunk.type not in self.processing_stats["documents_by_type"]:
                self.processing_stats["documents_by_type"][chunk.type] = 0
            self.processing_stats["documents_by_type"][chunk.type] += 1
        
        self.processing_stats["total_chunks"] += len(chunks)
        
        # Summary
        doc_chunks = len(chunks)
        doc_types = {}
        for chunk in chunks:
            doc_types[chunk.type] = doc_types.get(chunk.type, 0) + 1
        
        type_breakdown = ", ".join([f"{k}={v}" for k, v in doc_types.items()])
        logger.info(f"✅ Completed: {doc_chunks} chunks ({type_breakdown})")
    
    def _save_chunk(self, chunk: LegalChunk):
        """
        Persist a single LegalChunk to JSON file.
        
        Location: data/processed/chunks/{chunk_id}.json
        Format: Full Pydantic model_dump() with all fields
        
        Args:
            chunk: LegalChunk instance to persist
        """
        chunk_file = self.chunks_dir / f"{chunk.chunk_id}.json"
        chunk_data = chunk.model_dump(exclude_none=False)
        chunk_file.write_text(
            json.dumps(chunk_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
    
    def _save_relationships_csv(self):
        """
        Generate Neo4j relationships CSV from all chunks.
        
        Spec requirement (chunking.md):
        - Parent-child relationships: type="HAS_CHILD", source=parent_id, target=child_id
        - Cross-reference relationships: type="REFERENCES", source=chunk_id, target=cross_ref
        
        Output: data/processed/graph/relationships.csv with columns:
            source, relationship_type, target, weight
        """
        logger.info("\n" + "=" * 70)
        logger.info("GENERATING NEO4J RELATIONSHIPS CSV")
        logger.info("=" * 70)
        
        relationships = []
        
        # Extract parent-child and cross-reference edges
        for chunk in self.all_chunks:
            # Parent-child relationships
            if chunk.parent_id:
                relationships.append({
                    "source": chunk.parent_id,
                    "relationship_type": "HAS_CHILD",
                    "target": chunk.chunk_id,
                    "weight": 1.0
                })
            
            # Cross-reference relationships (detected legal refs → graph edges)
            for cross_ref in chunk.cross_references:
                relationships.append({
                    "source": chunk.chunk_id,
                    "relationship_type": "REFERENCES",
                    "target": cross_ref,
                    "weight": 0.5
                })
        
        # Write CSV
        csv_file = self.graph_dir / "relationships.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["source", "relationship_type", "target", "weight"])
            writer.writeheader()
            writer.writerows(relationships)
        
        logger.info(f"✓ Generated {len(relationships)} relationships")
        logger.info(f"✓ Saved to: {csv_file}")
    
    def _save_summary_report(self):
        """
        Generate markdown summary report of pipeline execution.
        
        Contains:
        - Execution timestamp and configuration
        - Document processing statistics
        - Chunk breakdown by type
        - Output file locations
        - Next steps for vector/graph indexing
        """
        logger.info("\n" + "=" * 70)
        logger.info("GENERATING SUMMARY REPORT")
        logger.info("=" * 70)
        
        timestamp = datetime.now().isoformat()
        
        report_lines = [
            "# Clause Ingestion Pipeline Summary",
            "",
            f"**Generated**: {timestamp}",
            "",
            "## Specification Compliance",
            "✅ Spec Document: `context/chunking.md`",
            "✅ Pipeline: 3-layer hierarchical chunking",
            "✅ Chunker: `clause.ingestion.chunkers.section_chunker.SectionChunker`",
            "",
            "## Execution Summary",
            f"- **Total Documents Processed**: {self.processing_stats['successful_documents']}/{self.processing_stats['total_documents']}",
            f"- **Documents Failed**: {self.processing_stats['failed_documents']}",
            f"- **Total Chunks Generated**: {self.processing_stats['total_chunks']}",
            "",
            "## Chunk Breakdown",
        ]
        
        # Add breakdown by chunk type
        for chunk_type in ["document", "parent", "child", "table"]:
            count = self.processing_stats["documents_by_type"].get(chunk_type, 0)
            if count > 0:
                report_lines.append(f"- **{chunk_type.capitalize()} chunks**: {count}")
        
        report_lines.extend([
            "",
            "## Output Directory Structure",
            f"```",
            f"{self.processed_dir}/",
            f"├── chunks/             # Individual JSON files (one per chunk)",
            f"│   ├── {{ACT}}_DOC.json",
            f"│   ├── {{ACT}}_S{{n}}.json         (parent chunks)",
            f"│   ├── {{ACT}}_S{{n}}_{{m}}.json    (child chunks)",
            f"│   └── {{ACT}}_S{{n}}_T{{k}}.json   (table chunks)",
            f"├── graph/",
            f"│   └── relationships.csv  # Neo4j edge import",
            f"└── entities/",
            f"    └── summary.md         # This file",
            f"```",
            "",
            "## Next Steps",
            "",
            "### 1. Vector Indexing (Qdrant)",
            "```bash",
            "# Embed child chunks via SentenceTransformer and index to Qdrant",
            "python -m clause.indexing.vector_index",
            "```",
            "",
            "### 2. Graph Indexing (Neo4j)",
            "```bash",
            "# Import chunks as nodes and relationships.csv as edges",
            "neo4j-admin import --nodes data/processed/graph/chunks.csv \\",
            "                   --relationships data/processed/graph/relationships.csv",
            "```",
            "",
            "### 3. BM25 Indexing (Elasticsearch/Whoosh)",
            "```bash",
            "# Build sparse index for keyword search",
            "python -m clause.indexing.bm25_index",
            "```",
            "",
            "### 4. Hybrid Retrieval",
            "```bash",
            "# Test vector + BM25 + graph fusion",
            "python -m clause.retrieval.hybrid_search",
            "```",
            "",
            "## Chunk Type Definitions (Spec Compliance)",
            "",
            "### Layer 1: Document Metadata (type='document')",
            "- **Purpose**: Graph node for document-level metadata",
            "- **Fields**: chunk_id (format: {ACT}_DOC), name, year, ministry, total_sections",
            "- **Retrieval**: Not embedded (metadata only)",
            "",
            "### Layer 2: Parent Chunks (type='parent')",
            "- **Purpose**: Generation context (sent to LLM with children)",
            "- **Token Range**: 512–1024 tokens",
            "- **Content**: Complete legal section with all sub-sections intact",
            "- **Chunk ID Format**: {ACT}_S{n} (e.g., CA2013_S42)",
            "- **Retrieval**: Not embedded directly; used as context when child is retrieved",
            "",
            "### Layer 3: Child Chunks (type='child')",
            "- **Purpose**: Vector search and BM25 indexing",
            "- **Token Range**: 128–256 tokens",
            "- **Content**: One sub-section or logical clause",
            "- **Chunk ID Format**: {ACT}_S{n}_{m} (e.g., CA2013_S42_3)",
            "- **Retrieval**: Primary retrieval unit (embedded + indexed)",
            "- **Context**: ±2 sentence_window for generation-time context",
            "",
            "### Tables (type='table')",
            "- **Purpose**: Structured data (fee schedules, penalty tables)",
            "- **Chunk ID Format**: {ACT}_S{n}_T{k}",
            "- **Fields**: raw_text (original), structured (list[dict] parsed)",
            "- **Retrieval**: Embedded as child chunks",
            "",
            "## Spec Compliance Checklist",
            "",
            "### Implemented Requirements",
            "- ✅ 3-layer hierarchical chunking (document, parent, child)",
            "- ✅ Deterministic chunk IDs (ACT_S{n} format)",
            "- ✅ Token counting via tiktoken cl100k_base",
            "- ✅ Token bounds enforcement (512-1024 parent, 128-256 child)",
            "- ✅ Proviso merging (enforced: 'Provided that' never standalone)",
            "- ✅ Explanation merging (enforced: 'Explanation —' never standalone)",
            "- ✅ Cross-reference detection (Section X, Rule Y, Schedule Z patterns)",
            "- ✅ Table extraction with structured parsing",
            "- ✅ Sentence windows (±2 sentences on child chunks)",
            "- ✅ Parent-child relationship tracking",
            "",
            "### Next Phase: Graph Construction",
            "- ⏳ Neo4j nodes from all chunks",
            "- ⏳ Edges from parent-child relationships",
            "- ⏳ Edges from cross-references",
        ])
        
        # Write report
        report_file = self.entities_dir / "SUMMARY.md"
        report_file.write_text("\n".join(report_lines), encoding='utf-8')
        logger.info(f"✓ Saved: {report_file}")
    
    def _print_statistics(self):
        """Print final execution statistics to console and log."""
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✅ Documents Processed: {self.processing_stats['successful_documents']}/{self.processing_stats['total_documents']}")
        logger.info(f"❌ Documents Failed: {self.processing_stats['failed_documents']}")
        logger.info(f"📊 Total Chunks: {self.processing_stats['total_chunks']}")
        
        if self.processing_stats["documents_by_type"]:
            logger.info("📈 Breakdown:")
            for chunk_type, count in self.processing_stats["documents_by_type"].items():
                logger.info(f"    - {chunk_type}: {count}")
        
        logger.info(f"📁 Output: {self.processed_dir}")
        logger.info("=" * 70)


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run()
