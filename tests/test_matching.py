from unittest.mock import patch


def _create_posting(client):
    return client.post(
        "/job-postings",
        json={"company": "NVIDIA", "role": "SWE Intern", "raw_text": "Python and CUDA required."},
    ).json()


def _fake_match_result():
    return {
        "matched_required_skills": ["Python"],
        "missing_required_skills": ["CUDA"],
        "matched_preferred_skills": [],
        "missing_preferred_skills": [],
        "match_score": 0.5,
        "total_required": 2,
        "total_preferred": 0,
        "document_ids": [1],
        "answer": "Matches on Python, missing CUDA.",
        "citations": [{"chunk_id": "document:1:0:abc123", "quote": "Python experience."}],
        "sufficient_context": True,
    }


def test_match_returns_404_for_missing_job_posting(client):
    response = client.post("/job-postings/9999/match", json={})
    assert response.status_code == 404


def test_match_returns_400_when_no_documents_exist(client):
    posting = _create_posting(client)
    response = client.post(f"/job-postings/{posting['id']}/match", json={})
    assert response.status_code == 400


def test_match_returns_404_for_unknown_document_ids(client):
    posting = _create_posting(client)
    response = client.post(f"/job-postings/{posting['id']}/match", json={"document_ids": [9999]})
    assert response.status_code == 404


def test_match_returns_scored_result_and_saves_an_analysis_run(client, db_session):
    from backend.models import Document, DocumentType, AnalysisRun

    posting = _create_posting(client)
    db_session.add(Document(document_type=DocumentType.RESUME, title="Resume", raw_text="Python.", content_hash="hash123"))
    db_session.commit()

    with patch("backend.main.match_job_posting", return_value=_fake_match_result()):
        response = client.post(f"/job-postings/{posting['id']}/match", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["match_score"] == 0.5
    assert body["matched_required_skills"] == ["Python"]

    saved = db_session.query(AnalysisRun).filter(AnalysisRun.extractor_type == "match").all()
    assert len(saved) == 1
    assert saved[0].job_posting_id == posting["id"]
