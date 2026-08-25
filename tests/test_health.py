"""Health endpoint tests."""


def test_root_health_returns_json(client):
    r = client.get("/health")
    assert r.status_code in (200, 503)  # degraded without a trained model
    body = r.get_json()
    assert "status" in body
    assert "model_loaded" in body
    assert "database" in body
    assert "version" in body


def test_api_v1_health_shape(client):
    r = client.get("/api/v1/health")
    assert r.status_code in (200, 503)
    body = r.get_json()
    assert body["success"] is True
    data = body["data"]
    for key in ("status", "model_loaded", "model_version", "database", "version"):
        assert key in data


def test_health_does_not_run_inference(client):
    """Health must be cheap — it should respond even with no model present."""
    r = client.get("/health")
    assert r.status_code == 503  # model absent -> honest degraded status
    assert r.get_json()["model_loaded"] is False