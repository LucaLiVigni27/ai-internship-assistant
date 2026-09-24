def _upload(client, text=b"Python, SQL, and Docker experience.", filename="resume.txt", title="My Resume", document_type="resume"):
    return client.post(
        "/documents/upload",
        files={"file": (filename, text, "text/plain")},
        data={"document_type": document_type, "title": title},
    )


def test_upload_document_returns_200_and_hash(client):
    response = _upload(client)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "My Resume"
    assert body["document_type"] == "resume"
    assert body["source_filename"] == "resume.txt"
    assert body["content_hash"]


def test_duplicate_content_returns_the_same_document(client):
    first = _upload(client).json()
    second = _upload(client, title="Different Title").json()
    assert first["id"] == second["id"]


def test_unsupported_file_type_is_rejected(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("resume.exe", b"binary junk", "application/octet-stream")},
        data={"document_type": "resume", "title": "My Resume"},
    )
    assert response.status_code == 400


def test_blank_file_returns_422(client):
    response = _upload(client, text=b"   ")
    assert response.status_code == 422


def test_list_documents_filters_by_type(client):
    _upload(client, text=b"Resume content.", filename="a.txt", title="Resume", document_type="resume")
    _upload(client, text=b"Project write-up.", filename="b.txt", title="Project", document_type="project")

    resumes = client.get("/documents", params={"document_type": "resume"}).json()
    assert len(resumes) == 1
    assert resumes[0]["document_type"] == "resume"

    everything = client.get("/documents").json()
    assert len(everything) == 2


def test_get_nonexistent_document_returns_404(client):
    response = client.get("/documents/9999")
    assert response.status_code == 404


def test_delete_document_then_404(client):
    document = _upload(client).json()
    client.delete(f"/documents/{document['id']}")
    response = client.get(f"/documents/{document['id']}")
    assert response.status_code == 404
