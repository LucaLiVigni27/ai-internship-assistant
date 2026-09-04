def test_job_description_analyzer_detects_required_skills(client):
    response = client.post(
        "/job-descriptions/analyze",
        json={"text": "Required: Python, SQL, Docker, FastAPI, PyTorch, and Linux experience."},
    )

    assert response.status_code == 200
    data = response.json()

    required_names = {s["name"] for s in data["required_skills"]}
    assert "Python" in required_names
    assert "SQL" in required_names
    assert "Docker" in required_names


def test_analyzer_rejects_blank_text(client):
    response = client.post("/job-descriptions/analyze", json={"text": "   "})
    assert response.status_code == 400


def test_analyzer_no_duplicate_node_matches(client):
    response = client.post(
        "/job-descriptions/analyze",
        json={"text": "Required: Node.js and Node experience."},
    )
    assert response.status_code == 200
    data = response.json()
    node_matches = [s for s in data["required_skills"] if s["name"] == "Node.js"]
    assert len(node_matches) == 1  # deduped, not counted twice


def test_analyzer_ambiguous_skill_not_matched_lowercase(client):
    response = client.post(
        "/job-descriptions/analyze",
        json={"text": "Please go to our office and react quickly to customer needs."},
    )
    assert response.status_code == 200
    data = response.json()
    all_names = {s["name"] for lst in ("required_skills", "preferred_skills", "mentioned_skills") for s in data[lst]}
    assert "Go" not in all_names
    assert "React" not in all_names


def test_analyzer_negated_skill_goes_to_mentioned(client):
    response = client.post(
        "/job-descriptions/analyze",
        json={"text": "Required: Python. No experience with Kubernetes required."},
    )
    assert response.status_code == 200
    data = response.json()

    mentioned_names = {s["name"] for s in data["mentioned_skills"]}
    required_names = {s["name"] for s in data["required_skills"]}
    assert "Kubernetes" in mentioned_names
    assert "Kubernetes" not in required_names
