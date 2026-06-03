"""
RAGAS-based evaluation of the Clause RAG pipeline.

Uses Ollama (local, free) as the LLM judge instead of OpenAI.
Metrics computed:
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
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Ollama judge ───────────────────────────────────────────────────────────────

def _llm_judge(prompt: str) -> str:
    """Call Ollama for LLM-as-judge scoring."""
    from openai import OpenAI
    from clause.config import settings

    client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")
    r = client.chat.completions.create(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.0,
    )
    return r.choices[0].message.content.strip()


def _parse_score(text: str) -> float:
    """Extract a 0.0–1.0 score from LLM output."""
    matches = re.findall(r'\b(0\.\d+|1\.0|0|1)\b', text)
    if matches:
        return max(0.0, min(1.0, float(matches[0])))
    return 0.5  # default if parse fails


# ── Individual metrics ─────────────────────────────────────────────────────────

def score_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """
    Faithfulness: is every claim in the answer supported by retrieved context?
    Score 0-1. 1 = fully grounded, 0 = hallucinated.
    """
    context_text = "\n---\n".join(contexts[:5])
    prompt = f"""You are evaluating a RAG system's answer for FAITHFULNESS.
Faithfulness measures whether ALL claims in the answer are supported by the retrieved context.

Question: {question}

Retrieved Context:
{context_text}

Answer to evaluate:
{answer}

Score the faithfulness from 0.0 to 1.0:
- 1.0: Every claim in the answer is explicitly supported by the context
- 0.7: Most claims are supported, minor unsupported details
- 0.5: About half the claims are supported
- 0.3: Most claims are not supported by context
- 0.0: Answer is completely unsupported or contradicts context

Return ONLY a number between 0.0 and 1.0, nothing else."""
    return _parse_score(_llm_judge(prompt))


def score_answer_relevancy(question: str, answer: str) -> float:
    """
    Answer Relevancy: does the answer directly address the question?
    Score 0-1. 1 = perfectly on-topic, 0 = completely off-topic.
    """
    prompt = f"""You are evaluating a RAG system's answer for ANSWER RELEVANCY.
Answer relevancy measures how directly the answer addresses the question asked.

Question: {question}

Answer to evaluate:
{answer}

Score the answer relevancy from 0.0 to 1.0:
- 1.0: The answer directly and completely addresses the question
- 0.7: The answer mostly addresses the question with minor gaps
- 0.5: The answer partially addresses the question
- 0.3: The answer is tangentially related to the question
- 0.0: The answer does not address the question at all

Return ONLY a number between 0.0 and 1.0, nothing else."""
    return _parse_score(_llm_judge(prompt))


def score_context_precision(question: str, contexts: list[str]) -> float:
    """
    Context Precision: what fraction of retrieved chunks are actually relevant?
    Score 0-1. 1 = all chunks relevant, 0 = no relevant chunks.
    """
    if not contexts:
        return 0.0

    relevant_count = 0
    for ctx in contexts:
        prompt = f"""Is this retrieved context chunk relevant to answering the question?

Question: {question}

Context chunk:
{ctx[:500]}

Reply with 1 if relevant, 0 if not relevant. Return ONLY the number."""
        score = _parse_score(_llm_judge(prompt))
        if score >= 0.5:
            relevant_count += 1

    return relevant_count / len(contexts)


def score_context_recall(question: str, answer: str, ground_truth: str, contexts: list[str]) -> float:
    """
    Context Recall: does the retrieved context contain all info needed for a correct answer?
    Uses ground truth as reference. Score 0-1.
    """
    context_text = "\n---\n".join(contexts[:5])
    prompt = f"""You are evaluating a RAG system for CONTEXT RECALL.
Context recall measures whether the retrieved context contains all the information
needed to produce the ground truth answer.

Question: {question}

Ground Truth Answer (expert-written):
{ground_truth}

Retrieved Context:
{context_text}

Score the context recall from 0.0 to 1.0:
- 1.0: All information in the ground truth is present in the retrieved context
- 0.7: Most information is present, minor gaps
- 0.5: About half the needed information is present
- 0.3: Most needed information is missing
- 0.0: Retrieved context contains none of the information needed

Return ONLY a number between 0.0 and 1.0, nothing else."""
    return _parse_score(_llm_judge(prompt))


# ── Main eval function ─────────────────────────────────────────────────────────

def run_ragas_eval(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],      # list of context lists (one per question)
    ground_truths: list[str],
    verbose: bool = True,
) -> dict:
    """
    Run RAGAS-style evaluation using Ollama as the LLM judge.

    Args:
        questions:    List of question strings
        answers:      List of generated answers (one per question)
        contexts:     List of context chunk text lists (one list per question)
        ground_truths: List of reference answers (one per question)
        verbose:      Print per-question scores

    Returns:
        {
            "faithfulness":      float   (mean)
            "answer_relevancy":  float   (mean)
            "context_precision": float   (mean)
            "context_recall":    float   (mean)
            "avg_score":         float   (mean of all 4)
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
        cr = score_context_recall(q, a, gt, ctx)

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
