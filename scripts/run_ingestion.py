"""CLI entry point for ingestion pipeline."""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path

from clause.ingestion.pipeline import run_ingestion_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ingestion.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Clause ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with enrichment
  python -m scripts.run_ingestion --source data/raw/ --output data/processed/
  
  # Run pipeline without enrichment (faster for testing)
  python -m scripts.run_ingestion --source data/raw/ --skip-enrichment
  
  # Run on specific directory
  python -m scripts.run_ingestion --source data/raw/companies_act/
        """,
    )

    parser.add_argument(
        "--source",
        type=str,
        default="data/raw/",
        help="Path to directory containing raw PDFs/HTMLs (default: data/raw/)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/",
        help="Path to output directory (default: data/processed/)",
    )

    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Skip Claude enrichment step (faster for testing)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Update logging level
    logging.getLogger().setLevel(args.log_level)

    # Validate paths
    source_path = Path(args.source)
    if not source_path.exists():
        logger.error(f"Source directory not found: {args.source}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Ingestion Configuration:")
    logger.info(f"  Source: {args.source}")
    logger.info(f"  Output: {args.output}")
    logger.info(f"  Skip enrichment: {args.skip_enrichment}")
    logger.info("")

    try:
        # Run pipeline
        result = asyncio.run(
            run_ingestion_pipeline(
                source_dir=args.source,
                output_dir=args.output,
                skip_enrichment=args.skip_enrichment,
            )
        )

        # Save result to JSON
        result_file = output_path / "pipeline_result.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Pipeline result saved to {result_file}")

        # Print summary
        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        print("=" * 60)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
