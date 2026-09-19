"""
Combines lexical (BM25/FTS5) and vector (embedding) search results using 
Reciprocal Rank Fusion (RRF): A way to merge rankings from methods whose raw scores aren't on comparable scales

RRF contribution per result = 1 / (k + rank), rank starting at 1. A chunk found by both methods accumulates contributions
from each, where a chunk found by only one still scores meaningfully rather than being penalized for the other method's silence on it.
"""

from backend.lexical_search import search_lexical
from backend.vector_store import search_vector

RRF_K = 60

def reciprocal_rank_fusion(result_lists: list[list[dict]], top_k: int = 5) -> list[dict]:
    scores: dict[str, float] = {}
    chunk_data: dict[str, dict] = {}

    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            chunk_id = item["chunk_id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
            chunk_data.setdefault(chunk_id, item)

    ranked_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

    return [
        {**chunk_data[cid], "rrf_score": scores[cid]}
        for cid in ranked_ids[:top_k]
    ]

def hybrid_search(query: str, top_k: int = 5, source_type: str | None = None, fusion_pool_size: int = 20) -> list[dict]: 
    # fusion_pool_size controls how many results each method contributes to the fusion pool before merging. 
    # Pulling for a wider pool for each method before fusing, allows for good fesults from either method to surface, despite them results intially lying outside the top-5 of its method
    lexical_results = search_lexical(query, top_k=fusion_pool_size, source_type=source_type)
    vector_results = search_vector(query, top_k=fusion_pool_size, source_type=source_type)
    return reciprocal_rank_fusion([lexical_results, vector_results], top_k=top_k)