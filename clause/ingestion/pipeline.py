"""
Main Ingestion Pipeline Orchestrator
Parses PDFs → Chunks → Extracts entities → Saves to processed/
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

from clause.ingestion.parsers.pdf_parser import PDFParser
from clause.ingestion.chunkers.section_chunker import SectionChunker, LegalChunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Main pipeline for document ingestion"""
    
    def __init__(self, data_root: str = "data"):
        """
        Initialize pipeline
        
        Args:
            data_root: Root data directory
        """
        self.data_root = Path(data_root)
        self.raw_dir = self.data_root / "raw"
        self.processed_dir = self.data_root / "processed"
        self.chunks_dir = self.processed_dir / "chunks"
        self.entities_dir = self.processed_dir / "entities"
        self.graph_dir = self.processed_dir / "graph"
        
        # Create output directories
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.entities_dir.mkdir(parents=True, exist_ok=True)
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        
        # Document metadata
        self.document_configs = {
            "Companies_Act_2013": {
                "filename": "Companies_Act_2013.pdf",
                "act_name": "Companies Act 2013",
                "effective_date": "2013-09-12",
                "subfolder": "companies_act"
            },
            "Companies_Incorporation_Rules_2014": {
                "filename": "Companies_Incorporation_Rules_2014.pdf",
                "act_name": "Companies (Incorporation) Rules 2014",
                "effective_date": "2014-03-31",
                "subfolder": "companies_rules"
            },
            "Companies_Share_Capital_Rules_2014": {
                "filename": "Companies_Share_Capital_Rules_2014.pdf",
                "act_name": "Companies (Share Capital) Rules 2014",
                "effective_date": "2014-03-31",
                "subfolder": "companies_rules"
            },
            "Companies_Accounts_Rules_2014": {
                "filename": "Companies_Accounts_Rules_2014.pdf",
                "act_name": "Companies (Accounts) Rules 2014",
                "effective_date": "2014-03-31",
                "subfolder": "companies_rules"
            },
            "Companies_Meetings_Rules_2014": {
                "filename": "Companies_Meetings_Rules_2014.pdf",
                "act_name": "Companies (Meetings) Rules 2014",
                "effective_date": "2014-03-31",
                "subfolder": "companies_rules"
            },
            "Companies_Directors_Rules_2014": {
                "filename": "Companies_Directors_Rules_2014.pdf",
                "act_name": "Companies (Directors) Rules 2014",
                "effective_date": "2014-03-31",
                "subfolder": "companies_rules"
            },
            "SEBI_ICDR_Regulations_2018": {
                "filename": "SEBI_ICDR_Regulations_2018.pdf",
                "act_name": "SEBI (ICDR) Regulations 2018",
                "effective_date": "2018-06-08",
                "subfolder": "sebi"
            },
            "SEBI_AIF_Regulations_2012": {
                "filename": "SEBI_AIF_Regulations_2012.pdf",
                "act_name": "SEBI (AIF) Regulations 2012",
                "effective_date": "2012-12-14",
                "subfolder": "sebi"
            },
            "DPIIT_Startup_Recognition_Guidelines": {
                "filename": "DPIIT_Startup_Recognition_Guidelines.pdf",
                "act_name": "DPIIT Startup Recognition Guidelines",
                "effective_date": "2023-01-01",
                "subfolder": "dpiit"
            },
            "Startup_India_Tax_Exemption_80IAC": {
                "filename": "Startup_India_Tax_Exemption_80IAC.pdf",
                "act_name": "Startup India Tax Exemption (Section 80IAC)",
                "effective_date": "2016-04-01",
                "subfolder": "startup_tax"
            }
        }
        
        self.all_chunks: List[Chunk] = []
        self.all_elements: Dict = defaultdict(list)
        self.processing_stats = {
            "total_documents": 0,
            "successful_documents": 0,
            "failed_documents": 0,
            "total_chunks": 0,
            "total_elements": 0
        }
    
    def run(self, documents: List[str] = None):
        """
        Run the full pipeline
        
        Args:
            documents: List of document names to process (None = all)
        """
        logger.info("="*60)
        logger.info("CLAUSE INGESTION PIPELINE STARTING")
        logger.info("="*60)
        
        if documents is None:
            documents = list(self.document_configs.keys())
        
        self.processing_stats["total_documents"] = len(documents)
        
        for doc_name in documents:
            try:
                self._process_document(doc_name)
                self.processing_stats["successful_documents"] += 1
            except Exception as e:
                logger.error(f"Failed to process {doc_name}: {e}", exc_info=True)
                self.processing_stats["failed_documents"] += 1
        
        # Save consolidated outputs
        self._save_consolidated_outputs()
        
        # Print stats
        self._print_statistics()
    
    def _process_document(self, doc_name: str):
        """Process a single document"""
        config = self.document_configs[doc_name]
        filepath = self.raw_dir / config["subfolder"] / config["filename"]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {doc_name}")
        logger.info(f"File: {filepath}")
        logger.info(f"{'='*60}")
        
        # Step 1: Parse PDF
        logger.info("Step 1: Parsing PDF...")
        parser = PDFParser(str(filepath))
        parsed_data = parser.parse()
        logger.info(f"  ✓ Extracted text ({len(parsed_data['text'])} chars)")
        
        # Step 2: Chunk hierarchically
        logger.info("Step 2: Chunking hierarchically...")
        chunker = HierarchicalChunker(
            document_name=doc_name,
            act_name=config["act_name"],
            effective_date=config["effective_date"]
        )
        chunks = chunker.chunk(parsed_data["text"])
        logger.info(f"  ✓ Created {len(chunks)} chunks")
        self.all_chunks.extend(chunks)
        self.processing_stats["total_chunks"] += len(chunks)
        
        # Step 3: Extract special elements
        logger.info("Step 3: Extracting special elements...")
        extractor = SpecialElementsExtractor(
            document_name=doc_name,
            act_name=config["act_name"]
        )
        elements = extractor.extract_all(parsed_data["text"])
        
        total_elements = sum(len(v) for v in elements.values())
        logger.info(f"  ✓ Extracted {total_elements} special elements")
        
        for elem_type, elem_list in elements.items():
            self.all_elements[elem_type].extend(elem_list)
            self.processing_stats["total_elements"] += len(elem_list)
        
        # Step 4: Save chunks for this document
        logger.info("Step 4: Saving chunks...")
        self._save_document_chunks(doc_name, chunks)
        logger.info(f"  ✓ Saved {len(chunks)} chunks to {self.chunks_dir}")
        
        # Step 5: Save special elements for this document
        logger.info("Step 5: Saving special elements...")
        self._save_document_elements(doc_name, elements)
        logger.info(f"  ✓ Saved {total_elements} special elements")
        
        logger.info(f"✅ Completed: {doc_name}")
    
    def _save_document_chunks(self, doc_name: str, chunks: List[Chunk]):
        """Save chunks to individual JSON files"""
        for chunk in chunks:
            chunk_file = self.chunks_dir / f"{chunk.chunk_id}.json"
            chunk_file.write_text(
                json.dumps(chunk.to_dict(), indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
    
    def _save_document_elements(self, doc_name: str, elements: Dict):
        """Save special elements to JSON"""
        for elem_type, elem_list in elements.items():
            if elem_list:
                elem_file = self.entities_dir / f"{doc_name}_{elem_type}.json"
                elem_data = [
                    {
                        "element_id": e.element_id,
                        "element_type": e.element_type,
                        "text": e.text,
                        "section_reference": e.section_reference,
                        "metadata": e.metadata
                    }
                    for e in elem_list
                ]
                elem_file.write_text(
                    json.dumps(elem_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
    
    def _save_consolidated_outputs(self):
        """Save consolidated outputs for all documents"""
        logger.info("\n" + "="*60)
        logger.info("SAVING CONSOLIDATED OUTPUTS")
        logger.info("="*60)
        
        # Save all chunks metadata
        logger.info("Saving all chunks metadata...")
        all_chunks_metadata = [chunk.to_dict() for chunk in self.all_chunks]
        metadata_file = self.entities_dir / "all_chunks_metadata.json"
        metadata_file.write_text(
            json.dumps(all_chunks_metadata, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        logger.info(f"  ✓ Saved {len(all_chunks_metadata)} chunk records")
        
        # Save all special elements by type
        logger.info("Saving all special elements...")
        for elem_type, elem_list in self.all_elements.items():
            if elem_list:
                elem_data = [
                    {
                        "element_id": e.element_id,
                        "element_type": e.element_type,
                        "text": e.text,
                        "section_reference": e.section_reference,
                        "metadata": e.metadata
                    }
                    for e in elem_list
                ]
                elem_file = self.entities_dir / f"all_{elem_type}.json"
                elem_file.write_text(
                    json.dumps(elem_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
                logger.info(f"  ✓ Saved {len(elem_data)} {elem_type}")
        
        # Create graph relationships CSV (for Neo4j import)
        logger.info("Creating graph relationships CSV...")
        self._create_relationships_csv()
        logger.info(f"  ✓ Saved relationships to {self.graph_dir}/relationships.csv")
        
        # Create summary report
        logger.info("Creating summary report...")
        self._create_summary_report()
        logger.info(f"  ✓ Saved summary to {self.entities_dir}/SUMMARY.md")
    
    def _create_relationships_csv(self):
        """Create CSV for Neo4j graph import"""
        relationships = []
        
        # PARENT-CHILD relationships
        for chunk in self.all_chunks:
            if chunk.parent_chunk_id:
                relationships.append({
                    "source": chunk.parent_chunk_id,
                    "relationship_type": "HAS_CHILD",
                    "target": chunk.chunk_id,
                    "weight": 1.0
                })
            
            # CROSS-REFERENCE relationships
            for cross_ref in chunk.cross_references or []:
                relationships.append({
                    "source": chunk.chunk_id,
                    "relationship_type": "REFERENCES",
                    "target": cross_ref,
                    "weight": 0.5
                })
        
        # Save to CSV
        csv_file = self.graph_dir / "relationships.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("source,relationship_type,target,weight\n")
            for rel in relationships:
                f.write(f"{rel['source']},{rel['relationship_type']},{rel['target']},{rel['weight']}\n")
        
        logger.info(f"Created {len(relationships)} relationships")
    
    def _create_summary_report(self):
        """Create markdown summary report"""
        report_lines = [
            "# Clause Ingestion Pipeline Summary",
            "",
            "## Statistics",
            f"- **Total Documents Processed**: {self.processing_stats['successful_documents']}/{self.processing_stats['total_documents']}",
            f"- **Total Chunks Created**: {self.processing_stats['total_chunks']}",
            f"- **Total Special Elements Extracted**: {self.processing_stats['total_elements']}",
            f"- **Failed Documents**: {self.processing_stats['failed_documents']}",
            "",
            "## Element Breakdown",
        ]
        
        for elem_type, elem_list in self.all_elements.items():
            report_lines.append(f"- **{elem_type}**: {len(elem_list)}")
        
        report_lines.extend([
            "",
            "## Output Files",
            f"- **Chunks**: {self.chunks_dir}/",
            f"- **Entities**: {self.entities_dir}/",
            f"- **Graph**: {self.graph_dir}/",
            "",
            "## Next Steps",
            "1. Review chunks in `/data/processed/chunks/`",
            "2. Upload to Qdrant for vector search",
            "3. Import relationships into Neo4j",
            "4. Build BM25 index",
            "5. Test hybrid retrieval",
        ])
        
        report_file = self.entities_dir / "SUMMARY.md"
        report_file.write_text("\n".join(report_lines), encoding='utf-8')
    
    def _print_statistics(self):
        """Print final statistics"""
        logger.info("\n" + "="*60)
        logger.info("PIPELINE SUMMARY")
        logger.info("="*60)
        logger.info(f"✅ Successful: {self.processing_stats['successful_documents']}/{self.processing_stats['total_documents']}")
        logger.info(f"❌ Failed: {self.processing_stats['failed_documents']}")
        logger.info(f"📊 Total Chunks: {self.processing_stats['total_chunks']}")
        logger.info(f"🔍 Total Special Elements: {self.processing_stats['total_elements']}")
        logger.info(f"📁 Output Directory: {self.processed_dir}")
        logger.info("="*60)


if __name__ == "__main__":
    pipeline = IngestionPipeline()
    pipeline.run()
