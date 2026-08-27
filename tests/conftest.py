"""Shared pytest fixtures."""
import io

import numpy as np
import pytest
from PIL import Image

from app import create_app, db
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    # Use a throwaway SQLite DB per test run
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Tests intentionally run without the real ML model.
    MODEL_ENABLED = False


@pytest.fixture()
def app():
    """Create a fresh app per test.

    Note: we deliberately do NOT keep an app context open for the whole
    test — doing so makes flask-login cache the logged-in user on ``g``
    across separate test clients.  Each request must run in its own
    context, exactly like production.
    """
    application = create_app(TestConfig())
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    """A client logged in as a registered test user."""
    client.post(
        "/auth/register",
        data={"username": "testuser", "email": "test@example.com", "password": "password123"},
    )
    client.post("/auth/login", data={"username": "testuser", "password": "password123"})
    return client


def make_image(width=300, height=300, color=(120, 180, 90), fmt="PNG"):
    """Create an in-memory image that passes validation and the quality gate."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:, :] = color
    # Add noise so the blur score is high enough to pass the quality gate
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 60, size=(height, width, 3), dtype=np.uint8)
    arr = np.clip(arr.astype(int) + noise - 30, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format=fmt)
    buf.seek(0)
    return buf