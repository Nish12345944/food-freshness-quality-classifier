"""Security tests: headers, error handling, rate limiting."""
from app.config import Config


class RateLimitConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"


def test_security_headers_present(client):
    r = client.get("/")
    h = r.headers
    assert h.get("X-Content-Type-Options") == "nosniff"
    assert h.get("X-Frame-Options") == "DENY"
    assert h.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    csp = h.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp


def test_404_returns_branded_page(client):
    r = client.get("/this-page-does-not-exist")
    assert r.status_code == 404
    assert b"Return Home" in r.data


def test_api_404_returns_json(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    body = r.get_json()
    assert body["success"] is False


def test_no_plaintext_password_in_registration_response(client):
    r = client.post(
        "/auth/register",
        data={"username": "sec1", "email": "s@x.com", "password": "supersecret99"},
    )
    assert b"supersecret99" not in r.data


def test_rate_limiting_blocks_excess_requests():
    from app import create_app

    class StrictConfig(RateLimitConfig):
        pass

    application = create_app(StrictConfig())
    c = application.test_client()

    # Demo predict endpoint: 3 per minute — send 5 requests
    statuses = []
    for _ in range(5):
        r = c.post("/demo/predict", data={})
        statuses.append(r.status_code)
    assert 429 in statuses, f"expected a 429 among {statuses}"