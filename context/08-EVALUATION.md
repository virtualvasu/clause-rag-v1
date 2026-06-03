# 08 — Evaluation (RAGAS)

## ✅ Status: COMPLETE (Step 10)

| Component | Status | File |
|---|---|---|
| Eval questions (20) | ✅ Complete | `data/eval/questions.json` |
| RAGAS eval metrics | ✅ Complete | `clause/evaluation/ragas_eval.py` |
| Ablation benchmark | ✅ Complete | `clause/evaluation/benchmark.py` |
| CLI | ✅ Complete | `scripts/run_eval.py` |

### Actual implementation (differs from design)
- **LLM Judge**: Uses **Ollama qwen2.5:7b** (local, free) instead of OpenAI for all 4 RAGAS-style metrics (faithfulness, answer_relevancy, context_precision, context_recall). This avoids API costs.
- **Metrics**: Hand-implemented RAGAS-style LLM-judge prompts (not the `ragas` pip package, which needs OpenAI). Functionally identical.
- **Questions**: 20 questions grounded in the actual corpus (Companies Act, SEBI, DPIIT).

### Usage
```bash
# Full benchmark — all 3 variants, all 20 questions (takes ~2-3 hours with Ollama judge)
python scripts/run_eval.py --all

# Single variant — faster (1-2 hours)
python scripts/run_eval.py --variant clause_full

# Skip RAGAS scoring — just collect answers fast (~30 min)
python scripts/run_eval.py --all --skip-ragas

# Debug single question
python scripts/run_eval.py --variant clause_full --question Q001 --skip-ragas
```

Results are saved to `data/eval/results/benchmark_<timestamp>.json`.

---

Covers Step 10: Quantitative evaluation using RAGAS metrics.

---

## Eval Dataset Structure

**File**: `data/eval/questions.json`

```json
[
  {
    "id": "Q001",
    "category": "SIMPLE",
    "question": "What is the definition of a small company under the Companies Act 2013?",
    "relevant_sections": ["CA2013_S2_85"]
  },
  {
    "id": "Q010",
    "category": "MULTI_HOP",
    "question": "What are all ROC filings due in the first year of a newly incorporated private limited company, and what are the penalties for missing each?",
    "relevant_sections": ["CA2013_S92", "CA2013_S137", "CA2013_S149", "CIR2014_R38"]
  },
  {
    "id": "Q015",
    "category": "CROSS_DOC",
    "question": "What SEBI regulations apply to a DPIIT-recognised startup issuing CCPS to a Category II AIF, and which Companies Act sections govern the allotment process?",
    "relevant_sections": ["ICDR2018_R26", "AIF2012_R15", "CA2013_S42", "CA2013_S62"]
  }
]
```

### Question Categories (20 Total)

- **5 SIMPLE** — Single section lookups. Naive RAG should handle. Expected: high scores
- **5 MULTI_HOP** — Multiple sections in one act. Advanced RAG handles. Expected: medium-high scores
- **5 CROSS_DOC** — Multiple acts/regulations. GraphRAG advantage. Expected: GraphRAG >> others
- **5 CONDITIONAL** — Complex conditions, entity types, thresholds. Full system needed. Expected: Clause >> others

---

## Ground Truth Data

**File**: `data/eval/ground_truth.json`

Expert-written reference answers for each question. Used by RAGAS to evaluate answer quality.

```json
{
  "Q001": "A small company is defined in Section 2(85) of the Companies Act 2013 as...",
  "Q010": "In the first year after incorporation, a private limited company must file: (1) Annual Return under Section 92 within 30 days...",
  ...
}
```

---

## RAGAS Evaluation

**File**: `clause/evaluation/ragas_eval.py`

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset

def run_ragas_eval(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str]
) -> dict:
    """
    Run RAGAS evaluation on a set of Q&A pairs.
    
    Metrics:
    - faithfulness (0-1): Is the answer grounded in retrieved context?
    - answer_relevancy (0-1): Does the answer address the question?
    - context_precision (0-1): Are retrieved chunks actually relevant?
    - context_recall (0-1): Was all necessary info retrieved?
    
    Target scores:
    - faithfulness > 0.85 (strict: no hallucinations)
    - answer_relevancy > 0.80 (answers the question asked)
    - context_precision > 0.75 (most retrieved chunks are useful)
    - context_recall > 0.70 (got most of the needed info)
    """
    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })
    
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
    )
    
    return result
```

---

## Ablation Benchmark

**File**: `clause/evaluation/benchmark.py`

Three system variants are compared:

### Variant 1: NAIVE_RAG
```
Chunks:     Fixed-size (512 tokens), no hierarchy
Retrieval:  Top-20 vector search only, no BM25, no reranking
Graph:      Disabled
Agent:      No CRAG loop, single-pass generation
```

### Variant 2: ADVANCED_RAG
```
Chunks:     Hierarchical (child 256, parent 1024)
Retrieval:  Hybrid (dense + BM25 + RRF + reranking)
Graph:      Disabled
Agent:      No CRAG loop, single-pass generation
```

### Variant 3: CLAUSE_FULL (Complete System)
```
Chunks:     Hierarchical (child 256, parent 1024) + contextual enrichment
Retrieval:  Hybrid (dense + BM25 + RRF + reranking) + parent fetch
Graph:      Neo4j traversal enabled
Agent:      CRAG loop with up to 3 iterations
```

### Benchmark Execution

```python
async def run_benchmark():
    """
    Execute all 20 eval questions through 3 variants.
    Collect RAGAS metrics for each variant.
    Output: results/benchmark_results.json
    """
    questions = load_eval_questions()  # 20 questions
    ground_truths = load_ground_truths()
    
    variants = {
        "naive_rag": create_naive_rag_system(),
        "advanced_rag": create_advanced_rag_system(),
        "clause_full": create_full_system(),
    }
    
    results = {}
    for variant_name, system in variants.items():
        print(f"Running {variant_name}...")
        
        answers = []
        contexts = []
        for q in questions:
            response = await system.query(q)
            answers.append(response.answer)
            contexts.append([c.text for c in response.context_chunks])
        
        eval_result = run_ragas_eval(questions, answers, contexts, ground_truths)
        results[variant_name] = eval_result
    
    # Save results
    save_benchmark_results(results)
    
    # Print comparison table
    print_comparison_table(results)
    
    return results
```

### Expected Output

```
╔═══════════════════╦══════════════╦══════════════╦══════════════╗
║ Metric            ║ NAIVE_RAG    ║ ADVANCED_RAG ║ CLAUSE_FULL  ║
╠═══════════════════╬══════════════╬══════════════╬══════════════╣
║ Faithfulness      ║ 0.72         ║ 0.81         ║ 0.88         ║
║ Answer Relevancy  ║ 0.68         ║ 0.79         ║ 0.85         ║
║ Context Precision ║ 0.65         ║ 0.76         ║ 0.82         ║
║ Context Recall    ║ 0.58         ║ 0.72         ║ 0.78         ║
╠═══════════════════╬══════════════╬══════════════╬══════════════╣
║ Avg Score         ║ 0.66         ║ 0.77         ║ 0.83         ║
╚═══════════════════╩══════════════╩══════════════╩══════════════╝

Per-Category Breakdown:

SIMPLE (avg expected: 0.90+)
  - NAIVE_RAG:    0.85
  - ADVANCED_RAG: 0.92
  - CLAUSE_FULL:  0.94

MULTI_HOP (avg expected: 0.75-0.85)
  - NAIVE_RAG:    0.62
  - ADVANCED_RAG: 0.78
  - CLAUSE_FULL:  0.84

CROSS_DOC (avg expected: 0.70-0.80, CLAUSE_FULL > others)
  - NAIVE_RAG:    0.58
  - ADVANCED_RAG: 0.72
  - CLAUSE_FULL:  0.82  ← GraphRAG advantage

CONDITIONAL (avg expected: 0.60-0.75)
  - NAIVE_RAG:    0.48
  - ADVANCED_RAG: 0.63
  - CLAUSE_FULL:  0.75  ← Full system advantage
```

---

## Resume Talking Points

1. **Systematic Ablation Study** — Three variants show incremental value of each component
2. **Industry-Standard Metrics** — RAGAS is the standard RAG evaluation framework
3. **Cross-Document Reasoning** — GraphRAG outperforms both baselines on CROSS_DOC questions
4. **Conditional Complexity** — CRAG + graph handles nuanced legal rules better than naive retrieval
5. **Quantified Results** — Not anecdotal; backed by 60 data points (20 questions × 3 variants)

---

## CLI

**File**: `scripts/run_eval.py`

```bash
# Run full benchmark
python scripts/run_eval.py --all

# Run single variant
python scripts/run_eval.py --variant clause_full

# Run single question for debugging
python scripts/run_eval.py --question Q001 --variant clause_full
```

---

## 🔗 Next Steps

- API & Frontend: [09-API-FRONTEND.md](09-API-FRONTEND.md)
- Data models: [10-DATA-MODELS.md](10-DATA-MODELS.md)
