"""
Compares lexical search (FTS5/BM25) against vector search (Chroma) on the
labeled queries in tests/retrieval_eval_set.json. For each query, runs both
methods at top_k=5 and prints whether each found a relevant chunk and at
what rank, then prints aggregate Recall@5 and MRR per method, plus a list
of queries where the two methods disagreed sharply.

Run directly (not a pytest module):
    PYTHONPATH=. python3 tests/eval_retrieval.py
"""

import json
from pathlib import Path

from backend.lexical_search import search_lexical
from backend.vector_store import search_vector
from backend.hybrid_search import hybrid_search

EVAL_SET_PATH = Path("tests/retrieval_eval_set.json")
TOP_K = 5


def load_eval_set() -> list[dict]:
    with open(EVAL_SET_PATH) as f:
        return json.load(f)


def rank_of_first_relevant(results: list[dict], relevant_ids: set[str]) -> int | None:
    for i, r in enumerate(results):
        if r["chunk_id"] in relevant_ids:
            return i + 1
    return None


def score_query(results: list[dict], relevant_ids: set[str]) -> dict:
    found_ids = {r["chunk_id"] for r in results} & relevant_ids
    recall = len(found_ids) / len(relevant_ids) if relevant_ids else 1.0
    rank = rank_of_first_relevant(results, relevant_ids)
    reciprocal_rank = 1 / rank if rank else 0.0
    return {"recall": recall, "rank": rank, "reciprocal_rank": reciprocal_rank, "found_ids": found_ids}


def run_evaluation():
    eval_set = load_eval_set()

    lexical_scores = {"recall": [], "reciprocal_rank": []}
    vector_scores = {"recall": [], "reciprocal_rank": []}
    hybrid_scores = {"recall": [], "reciprocal_rank": []}
    disagreements = []

    for item in eval_set:
        query = item["query"]
        relevant_ids = set(item["relevant_chunk_ids"])

        lexical_results = search_lexical(query, top_k=TOP_K)
        vector_results = search_vector(query, top_k=TOP_K)
        hybrid_results = hybrid_search(query, top_k=TOP_K)

        lex_score = score_query(lexical_results, relevant_ids)
        vec_score = score_query(vector_results, relevant_ids)
        hyb_score = score_query(hybrid_results, relevant_ids) 

        lexical_scores["recall"].append(lex_score["recall"])
        lexical_scores["reciprocal_rank"].append(lex_score["reciprocal_rank"])
        vector_scores["recall"].append(vec_score["recall"])
        vector_scores["reciprocal_rank"].append(vec_score["reciprocal_rank"])
        hybrid_scores["recall"].append(hyb_score["recall"])
        hybrid_scores["reciprocal_rank"].append(hyb_score["reciprocal_rank"])

        print(f"[{item['id']}] \"{query}\" ({item['category']})")
        print(f"  lexical: recall={lex_score['recall']:.2f}  first relevant at rank {lex_score['rank'] or '-'}")
        print(f"  vector : recall={vec_score['recall']:.2f}  first relevant at rank {vec_score['rank'] or '-'}")
        print(f"  hybrid : recall={hyb_score['recall']:.2f}  first relevant at rank {hyb_score['rank'] or '-'}")

        lex_hit = bool(lex_score["found_ids"])
        vec_hit = bool(vec_score["found_ids"])
        if lex_hit != vec_hit:
            winner = "lexical" if lex_hit else "vector"
            disagreements.append({"id": item["id"], "query": query, "category": item["category"], "winner": winner})
            print(f"  >>> DISAGREEMENT: {winner} found a relevant chunk, the other found none")
        print()

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    print("=== Aggregate Results ===")
    for name, scores in [("LEXICAL", lexical_scores), ("VECTOR", vector_scores), ("HYBRID", hybrid_scores)]:
        print(f"\n{name}:")
        print(f"  Recall@{TOP_K}: {avg(scores['recall']):.2%}")
        print(f"  MRR:       {avg(scores['reciprocal_rank']):.3f}")

    print(f"\n=== Sharp Disagreements ({len(disagreements)}/{len(eval_set)} queries) ===")
    if disagreements:
        for d in disagreements:
            print(f"  [{d['id']}] \"{d['query']}\" ({d['category']}) - {d['winner']} found it, the other missed completely")
    else:
        print("  (none)")


if __name__ == "__main__":
    run_evaluation()
