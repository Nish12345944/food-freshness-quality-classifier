"""Prediction flow tests (upload page, demo, batch routing).

The trained model artifact is not committed to the repository, so these
tests verify the honest "model unavailable" behaviour plus the pages and
routing around prediction.  With a model artifact present the same
endpoints return real predictions.
"""
from conftest import make_image


def test_predict_without_model_redirects_with_error(auth_client):
    buf = make_image()
    r = auth_client.post(
        "/predict",
        data={"images": [(buf, "food.png")]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"model is not loaded" in r.data.lower() or b"not loaded" in r.data.lower()


def test_demo_page_renders(client):
    r = client.get("/demo")
    assert r.status_code == 200
    assert b"production AI model" in r.data


def test_demo_predict_without_model_returns_503(client):
    buf = make_image()
    r = client.post(
        "/demo/predict",
        data={"image": (buf, "food.png")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 503
    body = r.get_json()
    assert body["success"] is False


def test_dashboard_shows_model_status(auth_client):
    r = auth_client.get("/dashboard")
    assert r.status_code == 200
    # Honest indicator that predictions are unavailable without a model
    assert b"Model loading" in r.data or b"not loaded" in r.data


def test_batch_results_empty_redirects(auth_client):
    r = auth_client.get("/batch-results")
    assert r.status_code == 302