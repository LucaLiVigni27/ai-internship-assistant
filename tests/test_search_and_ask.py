from unittest.mock import patch


def _fake_chunk(chunk_id="job_posting:1:0:abc123"):
    return {"chunk_id": chunk_id, "text": "Python and Docker required.", "source_type": "job_posting", "source_id": 1, "rrf_score": 0.03}


def test_search_returns_hybrid_search_results(client):
    with patch("backend.main.hybrid_search", return_value=[_fake_chunk()]) as mocked:
        response = client.post("/search", json={"query": "Docker", "top_k": 3})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["chunk_id"] == "job_posting:1:0:abc123"
    mocked.assert_called_once_with("Docker", top_k=3, source_type=None)


def test_search_rejects_blank_query(client):
    response = client.post("/search", json={"query": "   "})
    assert response.status_code == 400


def test_ask_returns_answer_with_citations(client):
    fake_result = {
        "answer": "Two postings mention Docker.",
        "citations": [{"chunk_id": "job_posting:1:0:abc123", "quote": "Docker required."}],
        "sufficient_context": True,
    }
    with patch("backend.main.generate_answer", return_value=fake_result):
        response = client.post("/ask", json={"query": "Which postings mention Docker?"})

    assert response.status_code == 200
    body = response.json()
    assert body["sufficient_context"] is True
    assert body["citations"][0]["chunk_id"] == "job_posting:1:0:abc123"


def test_ask_reports_insufficient_context(client):
    fake_result = {
        "answer": "The indexed postings don't mention this.",
        "citations": [],
        "sufficient_context": False,
    }
    with patch("backend.main.generate_answer", return_value=fake_result):
        response = client.post("/ask", json={"query": "Something not in the corpus"})

    assert response.status_code == 200
    assert response.json()["sufficient_context"] is False
    assert response.json()["citations"] == []
