"""
Ablation benchmark: compare 3 system variants across 20 eval questions.

Variants (from 08-EVALUATION.md):
  naive_rag    — vector-only retrieval, no graph, no CRAG, no reranking
  advanced_rag — hybrid (vector + BM25 + RRF + reranking), no graph, no CRAG
  clause_full  — full system: hybrid + graph expansion + CRAG loop

Run: python scripts/run_eval.py --all
"""

import json
import logging
import statistics
import time
from datetime import datetime
from pathlib import Path

from clause.query import answer_query

logger = logging.getLogger(__name__)

DATA_DIR  = Path("data/eval")
RESULT_DIR = DATA_DIR / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)


# ── Variant definitions ────────────────────────────────────────────────────────

VARIANTS = {
    "naive_rag": {
        "use_graph":      False,
        "use_reranker":   False,
        "use_crag":       False,
        "top_k_retrieval": 5,
        "top_k_rerank":    5,
        "description": "Vector-only retrieval, no graph, no CRAG, no reranking",
    },
    "advanced_rag": {
        "use_graph":      False,
        "use_reranker":   True,
        "use_crag":       False,
        "top_k_retrieval": 20,
        "top_k_rerank":    5,
        "description": "Hybrid (vector + BM25 + RRF + reranking), no graph, no CRAG",
    },
    "clause_full": {
        "use_graph":      True,
        "use_reranker":   True,
        "use_crag":       True,
        "top_k_retrieval": 20,
        "top_k_rerank":    5,
        "description": "Full system: hybrid + graph expansion + CRAG loop",
    },
}


# ── Data loading ───────────────────────────────────────────────────────────────

def load_questions() -> list[dict]:
    path = DATA_DIR / "questions.json"
    if not path.exists():
        raise FileNotFoundError(f"Eval questions not found: {path}")
    return json.loads(path.read_text())


def load_ground_truths() -> dict[str, str]:
    path = DATA_DIR / "ground_truth.json"
    if not path.exists():
        logger.warning(f"Ground truth file not found: {path}. Using empty strings.")
        return {}
    return json.loads(path.read_text())


# ── Per-variant runner ─────────────────────────────────────────────────────────

def run_variant(
    variant_name: str,
    questions: list[dict],
    ground_truths: dict[str, str],
    question_ids: list[str] | None = None,
) -> dict:
    """
    Run all questions through a single system variant.
    Returns raw answers, contexts, and timing for RAGAS input.
    """
    config = VARIANTS[variant_name]
    results = []

    for q_data in questions:
        qid = q_data["id"]
        if question_ids and qid not in question_ids:
            continue

        question = q_data["question"]
        category = q_data["category"]
        gt = ground_truths.get(qid, "")

        logger.info(f"[{variant_name}] {qid} ({category}): {question[:60]}...")
        t0 = time.time()

        try:
            result = answer_query(
                query=question,
                use_graph=config["use_graph"],
                use_reranker=config["use_reranker"],
                use_crag=config["use_crag"],
                top_k_retrieval=config["top_k_retrieval"],
                top_k_rerank=config["top_k_rerank"],
            )
            answer   = result["answer"]
            contexts = result.get("context_texts", [])  # list of chunk text strings
            elapsed = time.time() - t0

            results.append({
                "id":       qid,
                "category": category,
                "question": question,
                "answer":   answer,
                "contexts": contexts,
                "ground_truth": gt,
                "crag_score":   result.get("crag_score", 0),
                "iterations":   result.get("iterations", 1),
                "latency_s":    round(elapsed, 2),
            })
            print(f"  ✓ {qid} ({elapsed:.1f}s) CRAG={result.get('crag_score', 0):.2f}")

        except Exception as e:
            logger.error(f"  ✗ {qid} failed: {e}")
            results.append({
                "id": qid, "category": category,
                "question": question, "answer": f"ERROR: {e}",
                "contexts": [], "ground_truth": gt,
                "crag_score": 0, "iterations": 0, "latency_s": 0,
            })

    return results


# ── Benchmark runner ───────────────────────────────────────────────────────────

def run_benchmark(
    variants_to_run: list[str] | None = None,
    question_ids:   list[str] | None = None,
    skip_ragas: bool = False,
) -> dict:
    """
    Run the full ablation benchmark across all (or specified) variants.

    Args:
        variants_to_run: Subset of ["naive_rag", "advanced_rag", "clause_full"]
        question_ids:    Subset of question IDs to run (e.g. ["Q001", "Q002"])
        skip_ragas:      Skip LLM-judge scoring (just collect answers)

    Returns:
        Full benchmark results dict
    """
    from clause.evaluation.ragas_eval import run_ragas_eval

    questions     = load_questions()
    ground_truths = load_ground_truths()
    variants_to_run = variants_to_run or list(VARIANTS.keys())

    all_results = {
        "timestamp":   datetime.now().isoformat(),
        "variants":    {},
        "comparison":  {},
    }

    for variant_name in variants_to_run:
        print(f"\n{'='*60}")
        print(f"Running variant: {variant_name}")
        print(f"Config: {VARIANTS[variant_name]['description']}")
        print(f"{'='*60}")

        raw = run_variant(variant_name, questions, ground_truths, question_ids)

        variant_result = {
            "config":       VARIANTS[variant_name],
            "raw_results":  raw,
            "ragas_scores": {},
        }

        if not skip_ragas and raw:
            print(f"\nScoring with RAGAS metrics (Ollama judge)...")
            valid = [r for r in raw if not r["answer"].startswith("ERROR")]
            if valid:
                ragas = run_ragas_eval(
                    questions     = [r["question"]   for r in valid],
                    answers       = [r["answer"]     for r in valid],
                    contexts      = [r["contexts"]   for r in valid],
                    ground_truths = [r["ground_truth"] for r in valid],
                    verbose       = True,
                )
                variant_result["ragas_scores"] = ragas

        # Per-category breakdown
        by_category = {}
        for r in raw:
            cat = r["category"]
            by_category.setdefault(cat, []).append(r.get("crag_score", 0))
        variant_result["avg_crag_by_category"] = {
            cat: round(statistics.mean(scores), 3)
            for cat, scores in by_category.items()
        }
        variant_result["avg_latency_s"] = round(
            statistics.mean(r["latency_s"] for r in raw if r["latency_s"] > 0), 2
        ) if raw else 0

        all_results["variants"][variant_name] = variant_result

    # Build comparison table
    print_comparison_table(all_results)

    # Save to disk
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULT_DIR / f"benchmark_{ts}.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"\nResults saved to: {out_path}")

    return all_results


# ── Pretty print ───────────────────────────────────────────────────────────────

def print_comparison_table(all_results: dict):
    variants = list(all_results["variants"].keys())
    metrics  = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "avg_score"]

    print(f"\n{'='*70}")
    print("BENCHMARK RESULTS")
    print(f"{'='*70}")

    col_w = 16
    header = f"{'Metric':<22}" + "".join(f"{v:<{col_w}}" for v in variants)
    print(header)
    print("-" * (22 + col_w * len(variants)))

    for metric in metrics:
        row = f"{metric:<22}"
        for v in variants:
            scores = all_results["variants"][v].get("ragas_scores", {})
            val = scores.get(metric, "—")
            row += f"{str(val):<{col_w}}"
        print(row)

    print(f"\n{'Avg Latency (s)':<22}" + "".join(
        f"{all_results['variants'][v].get('avg_latency_s', '—'):<{col_w}}"
        for v in variants
    ))

    print(f"\n{'='*70}")
    print("CRAG Score by Category")
    print(f"{'='*70}")
    for cat in ["SIMPLE", "MULTI_HOP", "CROSS_DOC", "CONDITIONAL"]:
        row = f"{cat:<22}"
        for v in variants:
            val = all_results["variants"][v].get("avg_crag_by_category", {}).get(cat, "—")
            row += f"{str(val):<{col_w}}"
        print(row)
