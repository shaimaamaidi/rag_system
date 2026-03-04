def test_health_endpoint(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_endpoint_stream(api_client):
    response = api_client.post("/api/v1/ask/", json={"question": "hello"})
    assert response.status_code == 200
    assert response.text == "part1part2"


def test_ask_endpoint_empty(api_client):
    response = api_client.post("/api/v1/ask/", json={"question": "   "})
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "APP_ERROR"


def test_ingest_endpoint_success(api_client):
    response = api_client.post(
        "/api/v1/ingest/",
        files={"file": ("file.pdf", b"abc", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_ingest_endpoint_unsupported(api_client):
    response = api_client.post(
        "/api/v1/ingest/",
        files={"file": ("file.txt", b"abc", "text/plain")},
    )
    assert response.status_code == 415
