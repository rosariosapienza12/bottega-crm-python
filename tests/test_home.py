from fastapi.testclient import TestClient

from app.main import app


def test_home_page_loads():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Bottega" in response.text
