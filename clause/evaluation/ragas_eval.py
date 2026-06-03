"""
RAGAS-based evaluation of the Clause RAG pipeline.

Judge model: Ollama qwen2.5:7b (local, free).

Key improvements over naive scoring:
  1. Chain-of-Thought (CoT) — model reasons step-by-step BEFORE giving a score
  2. Structured JSON output — {"reasoning": "...", "score": X} forces deliberation
  3. Concrete rubrics with legal-domain examples
  4. Robust JSON parsing with fallback regex extraction

Metrics:
  - faithfulness      (0-1): answer grounded in retrieved context?
  - answer_relevancy  (0-1): does the answer address the question?
  - context_precision (0-1): are retrieved chunks actually relevant?
  - context_recall    (0-1): was all necessary info retrieved?

Reference: 08-EVALUATION.md
"""

import json
import logging
import re
import statistics

logger = logging.getLogger(__name__)


# ── Ollama judge ───────────────────────────────────────────────────────────────

def _llm_judge(prompt: str, max_tokens: int = 400) -> str:
    """Call Ollama for LLM-as-judge scoring via direct HTTP POST."""
    import httpx
    from clause.config import settings

    url = settings.ollama_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.ollama_model,
        "messages": [{
            "role": "system",
            "content": (
                "You are a precise evaluation judge for RAG systems. "
                "Always follow the exact output format requested. "
                "Always return valid JSON with 'reasoning' and 'score' keys."
            ),
        }, {
            "role": "user",
            "content": prompt,
        }],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    with httpx.Client(timeout=120) as client:
        r = client.post(url, json=payload, headers={"Authorization": "Bearer ollama"})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


def _parse_cot_score(text: str) -> tuple[float, str]:
    """
    Extract score and reasoning from CoT JSON output.
    Tries JSON first, then falls back to regex extraction.

    Returns: (score 0.0-1.0, reasoning string)
    """
    # Try JSON parse (may be wrapped in markdown code block)
    json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            score = float(data.get("score", 0.5))
            reasoning = data.get("reasoning", "")
            return max(0.0, min(1.0, score)), reasoning
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: extract score from "score": X.X pattern
    score_match = re.search(r'"score"\s*:\s*([0-9.]+)', text)
    if score_match:
        try:
            score = float(score_match.group(1))
            return max(0.0, min(1.0, score)), ""
        except ValueError:
            pass

    # Last resort: find any standalone number
    num_matches = re.findall(r'\b(0\.\d+|1\.0|0\.0)\b', text)
    if num_matches:
        return max(0.0, min(1.0, float(num_matches[-1]))), ""

    logger.warning(f"Could not parse score from: {text[:100]}")
    return 0.5, ""  # neutral default


# ── Individual metrics (CoT-improved) ─────────────────────────────────────────

def score_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """
    Faithfulness: every claim in the answer must be traceable to the retrieved context.
    Uses CoT — model identifies each claim and checks it against context before scoring.
    """
    context_text = "\n---\n".join(c[:600] for c in contexts[:5])

    prompt = f"""You are evaluating a legal RAG system for FAITHFULNESS.

Definition: Faithfulness measures whether every factual claim in the generated answer
is explicitly supported by the retrieved context passages. An answer is unfaithful if
it introduces facts, section numbers, or legal rules NOT present in the context.

## Question
{question}

## Retrieved Context Passages
{context_text}

## Generated Answer
{answer}

## Your Task
Step 1 — List each distinct factual claim in the generated answer (max 5 claims).
Step 2 — For each claim, state whether it is SUPPORTED or NOT SUPPORTED by the context.
Step 3 — Calculate score = (supported claims) / (total claims).

## Scoring Guide
- 1.0: All claims are explicitly supported by the retrieved context
- 0.8: 4/5 claims supported (one minor unsupported detail)
- 0.6: 3/5 claims supported
- 0.4: 2/5 claims supported
- 0.0: Claims contradict context or come from outside knowledge

Important: If the answer explicitly says "the context does not contain...", that counts as faithful (score = 1.0).

Return ONLY valid JSON:
{{"reasoning": "<step-by-step claim analysis>", "score": <float 0.0-1.0>}}"""

    raw = _llm_judge(prompt, max_tokens=500)
    score, _ = _parse_cot_score(raw)
    return score


def score_answer_relevancy(question: str, answer: str) -> float:
    """
    Answer Relevancy: does the answer directly address what was asked?
    Uses CoT — model identifies question type and maps answer to it.
    """
    prompt = f"""You are evaluating a legal RAG system for ANSWER RELEVANCY.

Definition: Answer relevancy measures how directly and completely the generated answer
addresses the specific legal question asked. High relevancy means the answer targets
the exact question without excessive padding or tangential information.

## Question
{question}

## Generated Answer
{answer}

## Your Task
Step 1 — Identify the core legal concept being asked about (definition / procedure / penalty / condition).
Step 2 — Check if the answer directly addresses that concept.
Step 3 — Check if the answer stays on topic or drifts to unrelated information.
Step 4 — Assign a score.

## Scoring Guide
- 1.0: Answer directly and completely addresses the question
- 0.8: Answer addresses the question with minor tangential content
- 0.6: Answer partially addresses the question, misses important aspects
- 0.4: Answer is mostly about a related but different topic
- 0.2: Answer barely touches the question
- 0.0: Answer is completely off-topic or refused to answer

Note: An answer saying "the context does not contain enough information" is relevant
if the question is about something not in the corpus (score = 0.7).

Return ONLY valid JSON:
{{"reasoning": "<step-by-step analysis>", "score": <float 0.0-1.0>}}"""

    raw = _llm_judge(prompt, max_tokens=400)
    score, _ = _parse_cot_score(raw)
    return score


def score_context_precision(question: str, contexts: list[str]) -> float:
    """
    Context Precision: what fraction of retrieved chunks are actually useful?
    Evaluates ALL chunks together (not one-by-one) to avoid binary over-strictness.
    """
    if not contexts:
        return 0.0

    numbered = "\n".join(
        f"[Chunk {i+1}]: {ctx[:500]}" for i, ctx in enumerate(contexts)
    )

    prompt = f"""You are evaluating a legal RAG system for CONTEXT PRECISION.

Definition: Context precision measures what fraction of the retrieved context chunks
are actually useful for answering the question. A chunk is useful if it contains
information that is directly relevant to the question, even if the answer requires
reading multiple chunks together.

## Question
{question}

## Retrieved Context Chunks
{numbered}

## Your Task
Step 1 — For each chunk, state in ONE sentence what it is about.
Step 2 — Decide if each chunk is USEFUL or NOT USEFUL for answering the question.
  - USEFUL: Contains legal rules, definitions, procedures, or conditions directly related to the question topic
  - NOT USEFUL: Completely unrelated to the question topic
Step 3 — Calculate precision = (useful chunks) / (total chunks = {len(contexts)})

Important: Be GENEROUS — if a chunk is about the same legal topic even if not a perfect match, count it as USEFUL.

Return ONLY valid JSON:
{{"reasoning": "<per-chunk verdict>", "score": <float 0.0-1.0>}}"""

    raw = _llm_judge(prompt, max_tokens=500)
    score, _ = _parse_cot_score(raw)
    return score


def score_context_recall(question: str, ground_truth: str, contexts: list[str]) -> float:
    """
    Context Recall: does the retrieved context cover what the ground truth answer requires?
    If no ground truth available, uses question intent instead.
    """
    context_text = "\n---\n".join(c[:600] for c in contexts[:5])

    # If no ground truth, evaluate against question directly
    reference = ground_truth if ground_truth.strip() else f"[No ground truth — evaluate against question: {question}]"

    prompt = f"""You are evaluating a legal RAG system for CONTEXT RECALL.

Definition: Context recall measures whether the retrieved context contains all the
information needed to produce a complete answer. We compare what information IS
available in the context versus what the ideal answer WOULD REQUIRE.

## Question
{question}

## Reference Answer (what a complete answer should contain)
{reference}

## Retrieved Context
{context_text}

## Your Task
Step 1 — List the key information pieces needed to answer the question (max 4 points).
Step 2 — For each information piece, check if it's PRESENT in the retrieved context.
Step 3 — Calculate recall = (present pieces) / (total needed pieces).

## Scoring Guide
- 1.0: All needed information is present in the context
- 0.75: 3/4 needed pieces present
- 0.5: 2/4 needed pieces present
- 0.25: Only 1/4 needed pieces present
- 0.0: None of the needed information is present

Note: The context does NOT need to be in perfect form — if the information is there,
even if fragmented across chunks, count it as present.

Return ONLY valid JSON:
{{"reasoning": "<per-piece check>", "score": <float 0.0-1.0>}}"""

    raw = _llm_judge(prompt, max_tokens=500)
    score, _ = _parse_cot_score(raw)
    return score


# ── Main eval function ─────────────────────────────────────────────────────────

def run_ragas_eval(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
    verbose: bool = True,
) -> dict:
    """
    Run RAGAS-style evaluation using Ollama as the LLM judge.

    Args:
        questions:     List of question strings
        answers:       List of generated answers (one per question)
        contexts:      List of context chunk text lists (one list per question)
        ground_truths: List of reference answers (one per question)
        verbose:       Print per-question scores

    Returns:
        {
            "faithfulness":      float  (mean across questions)
            "answer_relevancy":  float
            "context_precision": float
            "context_recall":    float
            "avg_score":         float  (mean of all 4 metrics)
            "per_question":      list[dict]
        }
    """
    assert len(questions) == len(answers) == len(contexts) == len(ground_truths)

    per_question = []
    f_scores, ar_scores, cp_scores, cr_scores = [], [], [], []

    for i, (q, a, ctx, gt) in enumerate(zip(questions, answers, contexts, ground_truths)):
        logger.info(f"Scoring Q{i+1}/{len(questions)}: {q[:60]}...")

        f  = score_faithfulness(q, a, ctx)
        ar = score_answer_relevancy(q, a)
        cp = score_context_precision(q, ctx)
        cr = score_context_recall(q, gt, ctx)

        avg = statistics.mean([f, ar, cp, cr])

        result = {
            "question":          q,
            "faithfulness":      round(f, 3),
            "answer_relevancy":  round(ar, 3),
            "context_precision": round(cp, 3),
            "context_recall":    round(cr, 3),
            "avg":               round(avg, 3),
        }
        per_question.append(result)
        f_scores.append(f); ar_scores.append(ar)
        cp_scores.append(cp); cr_scores.append(cr)

        if verbose:
            print(f"  Q{i+1:02d} | F={f:.2f} AR={ar:.2f} CP={cp:.2f} CR={cr:.2f} avg={avg:.2f} | {q[:50]}")

    summary = {
        "faithfulness":      round(statistics.mean(f_scores), 3),
        "answer_relevancy":  round(statistics.mean(ar_scores), 3),
        "context_precision": round(statistics.mean(cp_scores), 3),
        "context_recall":    round(statistics.mean(cr_scores), 3),
        "avg_score":         round(statistics.mean(f_scores + ar_scores + cp_scores + cr_scores), 3),
        "per_question":      per_question,
    }
    return summary
