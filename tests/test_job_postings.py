def test_create_job_posting_returns_201_and_hash(client):
    response = client.post(
        "/job-postings",
        json = {"company": "NVIDIA", "role": "SWE Intern", "raw_text": "Python and CUDA required."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "NVIDIA"
    assert body["content_hash"] # non-empty

def test_duplicate_raw_text_returns_same_posting(client):
    payload = {"company": "NVIDIA", "role": "SWE Intern", "raw_text": "Python and CUDA required."}
    first = client.post("/job-postings", json=payload).json()
    second = client.post("/job-postings", json=payload).json()
    assert first["id"] == second["id"]


def test_blank_company_is_rejected(client):
    response = client.post(
        "/job-postings",
        json={"company": "   ", "role": "SWE Intern", "raw_text": "text"},
    )
    assert response.status_code == 422


def test_invalid_source_url_is_rejected(client):
    response = client.post(
        "/job-postings",
        json={"company": "NVIDIA", "role": "Intern", "raw_text": "text", "source_url": "not-a-url"},
    )
    assert response.status_code == 422


def test_get_nonexistent_job_posting_returns_404(client):
    response = client.get("/job-postings/9999")
    assert response.status_code == 404


def test_delete_job_posting_cascades_to_applications(client, db_session):
    from backend.models import Application

    posting = client.post(
        "/job-postings",
        json={"company": "NVIDIA", "role": "Intern", "raw_text": "text"},
    ).json()
    application = client.post(
        "/applications", json={"job_posting_id": posting["id"]}
    ).json()

    client.delete(f"/job-postings/{posting['id']}")

    remaining = db_session.query(Application).filter(Application.id == application["id"]).first()
    assert remaining is None