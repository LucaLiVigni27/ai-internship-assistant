from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_job_description_analyzer_detects_skills():
    response = client.post(
        "/job-descriptions/analyze",
        json={
            "text": "This role requires Python SQL, Docker, FastAPI, PyTorch, and Linux"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "Python"in data["matched_skills"]
    assert "SQL" in data["matched_skills"]
    assert "Docker" in data["matched_skills"]
