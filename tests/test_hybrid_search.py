from backend.hybrid_search import reciprocal_rank_fusion, RRF_K


def _result(chunk_id: str) -> dict:
    return {"chunk_id": chunk_id, "text": chunk_id, "source_type": "job_posting", "source_id": 1}


def test_chunk_found_by_both_methods_outranks_a_chunk_found_by_only_one():
    lexical = [_result("a"), _result("b")]
    vector = [_result("a"), _result("c")]
    fused = reciprocal_rank_fusion([lexical, vector], top_k=5)
    ids = [r["chunk_id"] for r in fused]
    assert ids[0] == "a"


def test_chunk_found_only_by_one_method_still_appears():
    lexical = [_result("a")]
    vector = [_result("b")]
    fused = reciprocal_rank_fusion([lexical, vector], top_k=5)
    ids = {r["chunk_id"] for r in fused}
    assert ids == {"a", "b"}


def test_rrf_score_matches_the_formula():
    lexical = [_result("a")]
    fused = reciprocal_rank_fusion([lexical], top_k=5)
    assert fused[0]["rrf_score"] == 1.0 / (RRF_K + 1)


def test_top_k_truncates_the_fused_results():
    lexical = [_result(str(i)) for i in range(10)]
    fused = reciprocal_rank_fusion([lexical], top_k=3)
    assert len(fused) == 3


def test_empty_result_lists_produce_no_matches():
    assert reciprocal_rank_fusion([[], []], top_k=5) == []


def test_earlier_rank_scores_higher_than_later_rank_from_the_same_method():
    lexical = [_result("first"), _result("second"), _result("third")]
    fused = reciprocal_rank_fusion([lexical], top_k=5)
    scores = [r["rrf_score"] for r in fused]
    assert scores == sorted(scores, reverse=True)
    assert [r["chunk_id"] for r in fused] == ["first", "second", "third"]
