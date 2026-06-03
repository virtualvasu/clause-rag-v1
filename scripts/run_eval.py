"""
CLI for running the evaluation benchmark.

Usage:
    python scripts/run_eval.py --all                         # full benchmark
    python scripts/run_eval.py --variant clause_full         # single variant
    python scripts/run_eval.py --variant clause_full --skip-ragas   # just collect answers
    python scripts/run_eval.py --question Q001 --variant clause_full # debug one question
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

from clause.evaluation.benchmark import run_benchmark, VARIANTS


def main():
    parser = argparse.ArgumentParser(description="Clause evaluation benchmark")
    parser.add_argument("--all",        action="store_true", help="Run all 3 variants")
    parser.add_argument("--variant",    choices=list(VARIANTS.keys()), help="Run a single variant")
    parser.add_argument("--question",   help="Run a single question ID (e.g. Q001)")
    parser.add_argument("--skip-ragas", action="store_true", help="Skip LLM-judge scoring (fast mode)")
    args = parser.parse_args()

    variants = None
    if args.all:
        variants = list(VARIANTS.keys())
    elif args.variant:
        variants = [args.variant]
    else:
        print("Specify --all or --variant <name>")
        parser.print_help()
        sys.exit(1)

    question_ids = [args.question] if args.question else None

    results = run_benchmark(
        variants_to_run=variants,
        question_ids=question_ids,
        skip_ragas=args.skip_ragas,
    )

    return results


if __name__ == "__main__":
    main()
