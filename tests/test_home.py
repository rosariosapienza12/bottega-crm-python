def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Bottega" in response.text
    assert "/registrati" in response.text


def test_security_headers_are_set(client):
    response = client.get("/")

    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_api_docs_are_not_public(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
