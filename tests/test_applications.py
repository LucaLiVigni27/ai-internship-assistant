def _create_posting(client):
    return client.post(
        "/job-postings",
        json={"company": "NVIDIA", "role": "SWE Intern", "raw_text": "Python and CUDA."},
    ).json()

def test_create_application_requires_existing_job_posting(client):
    response = client.post("/applications", json={"job_posting_id": 9999})
    assert response.status_code == 404

def test_create_application_defaults_to_saved_status(client):
    posting = _create_posting(client)
    response = client.post("/applications", json={"job_posting_id": posting["id"]})
    assert response.status_code == 200
    assert response.json()["status"] == "saved"

def test_list_applications_includes_nested_job_posting(client):
    posting = _create_posting(client)
    client.post("/applications", json={"job_posting_id": posting["id"]})

    response = client.get("/applications")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["job_posting"]["company"] == "NVIDIA"


def test_patch_application_updates_only_supplied_fields(client):
    posting = _create_posting(client)
    application = client.post("/applications", json={"job_posting_id": posting["id"]}).json()

    response = client.patch(f"/applications/{application['id']}", json={"status": "interviewing"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "interviewing"
    assert body["notes"] == application["notes"]  # untouched field preserved


def test_patch_nonexistent_application_returns_404(client):
    response = client.patch("/applications/9999", json={"status": "offer"})
    assert response.status_code == 404


def test_delete_application_returns_404_after_deletion(client):
    posting = _create_posting(client)
    application = client.post("/applications", json={"job_posting_id": posting["id"]}).json()

    client.delete(f"/applications/{application['id']}")
    response = client.get(f"/applications/{application['id']}")
    assert response.status_code == 404