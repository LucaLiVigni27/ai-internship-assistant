"""
Eval for Day 10 answer generation. Reuses the labeled queries from
retrieval_eval_set.json (Day 9) instead of a separate hand-labeled set.

For each query: run generate_answer(), then check
  1.) citation grounding: does every citation's quote actually appear
     verbatim in its cited chunk (validate_citations)
  2.) citation relevance: do citations point at chunks we already know
     are relevant (from retrieval_eval_set's relevant_chunk_ids), not
     just any retrieved chunk
  3.) sufficient_context correctness: expected value is derived live:
     True if any relevant_chunk_id shows up in this run's retrieved
     top-k, False if none do.

Run directly: PYTHONPATH=. python3 tests/eval_answers.py
"""

import json
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from backend.answer_generation import generate_answer, validate_citations

EVAL_SET_PATH = Path("tests/retrieval_eval_set.json")


def load_eval_set() -> list[dict]:
    with open(EVAL_SET_PATH) as f:
        return json.load(f)


def score_query(entry: dict, top_k: int = 5) -> dict:
    start = time.perf_counter()
    result = generate_answer(entry["query"], top_k=top_k)
    latency_ms = int((time.perf_counter() - start) * 1000)

    retrieved_ids = {c["chunk_id"] for c in result["retrieved_chunks"]}
    relevant_ids = set(entry["relevant_chunk_ids"])
    expected_sufficient = bool(retrieved_ids & relevant_ids)

    citation_check = validate_citations(result)

    cited_ids = {c["chunk_id"] for c in result["citations"]}
    relevant_citations = cited_ids & relevant_ids
    citation_relevance = len(relevant_citations) / len(cited_ids) if cited_ids else None

    return {
        "query": entry["query"],
        "category": entry["category"],
        "expected_sufficient_context": expected_sufficient,
        "actual_sufficient_context": result["sufficient_context"],
        "sufficient_context_correct": expected_sufficient == result["sufficient_context"],
        "citation_hallucination_rate": citation_check["citation_hallucination_rate"],
        "citation_hallucination_rate_normalized": citation_check["citation_hallucination_rate_normalized"],
        "invalid_citations": citation_check["invalid_citations"],
        "citation_relevance": citation_relevance,
        "latency_ms": latency_ms,
    }


def run_evaluation():
    eval_set = load_eval_set()
    results = []
    for i, entry in enumerate(eval_set, start=1):
        print(f"[{i}/{len(eval_set)}] running: \"{entry['query']}\"...")
        results.append(score_query(entry))

    print("=== Per-query ===")
    for r in results:
        flag = "OK" if r["sufficient_context_correct"] else "MISMATCH"
        rel = f"{r['citation_relevance']:.2f}" if r["citation_relevance"] is not None else "n/a"
        print(
            f"[{r['category']}] \"{r['query']}\" "
            f"expected_sufficient={r['expected_sufficient_context']} "
            f"actual={r['actual_sufficient_context']} [{flag}] "
            f"hallucination={r['citation_hallucination_rate']:.2%} "
            f"relevance={rel} "
            f"({r['latency_ms']}ms)"
        )

    print("\n=== Invalid citations (sample) ===")
    for r in results:
        for c in r["invalid_citations"]:
            print(f"  [{r['query']}] reason={c['reason']}")
            print(f"    chunk_id: {c['chunk_id']}")
            print(f"    quote:    {c['quote']!r}")

    n = len(results)
    sufficient_accuracy = sum(r["sufficient_context_correct"] for r in results) / n
    avg_hallucination = sum(r["citation_hallucination_rate"] for r in results) / n
    avg_hallucination_norm = sum(r["citation_hallucination_rate_normalized"] for r in results) / n
    relevance_scores = [r["citation_relevance"] for r in results if r["citation_relevance"] is not None]
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    avg_latency = sum(r["latency_ms"] for r in results) / n

    print("\n=== Aggregate ===")
    print(f"sufficient_context accuracy: {sufficient_accuracy:.2%}")
    print(f"citation hallucination rate (strict): {avg_hallucination:.2%}")
    print(f"citation hallucination rate (whitespace-normalized): {avg_hallucination_norm:.2%}")
    print(f"citation relevance (cited chunk is actually relevant): {avg_relevance:.2%}")
    print(f"avg latency: {avg_latency:.0f}ms")

    mismatches = [r for r in results if not r["sufficient_context_correct"]]
    if mismatches:
        print(f"\n=== Mismatches ({len(mismatches)}) ===")
        for r in mismatches:
            print(f"  \"{r['query']}\" expected={r['expected_sufficient_context']} got={r['actual_sufficient_context']}")


if __name__ == "__main__":
    run_evaluation()