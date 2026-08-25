"""API v1 endpoint tests (auth, history, errors)."""
from app import db
from app.models.analysis import Analysis


def test_api_history_requires_auth(client):
    r = client.get("/api/v1/history")
    assert r.status_code == 302  # login redirect for browser-style clients


def test_api_history_returns_envelope(auth_client):
    r = auth_client.get("/api/v1/history")
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] is True
    assert body["data"]["analyses"] == []
    assert body["data"]["total"] == 0


def test_api_analysis_owner_only(app, auth_client):
    with app.app_context():
        from app.models.user import User

        user = User.query.filter_by(username="testuser").first()
        analysis = Analysis(user_id=user.id, image_filename="x.png",
                            label="Fresh", confidence=0.9)
        db.session.add(analysis)
        db.session.commit()
        aid = analysis.id

    r = auth_client.get(f"/api/v1/analysis/{aid}")
    assert r.status_code == 200
    assert r.get_json()["data"]["label"] == "Fresh"

    # Another user gets 403
    c2 = app.test_client()
    c2.post("/auth/register", data={"username": "other", "email": "o@x.com",
                                    "password": "password123"})
    c2.post("/auth/login", data={"username": "other", "password": "password123"})
    r = c2.get(f"/api/v1/analysis/{aid}")
    assert r.status_code == 403


def test_api_predict_without_model_returns_503(auth_client):
    from conftest import make_image

    buf = make_image()
    r = auth_client.post(
        "/api/v1/predict",
        data={"image": (buf, "food.png")},
        content_type="multipart/form-data",
    )
    # Model artifact is not committed — service reports unavailable
    assert r.status_code == 503
    assert r.get_json()["success"] is False


def test_api_predict_missing_file_returns_400(auth_client):
    r = auth_client.post("/api/v1/predict", data={})
    assert r.status_code == 400


def test_api_unknown_route_returns_json_error(client):
    r = client.get("/api/v1/nonexistent")
    assert r.status_code == 404
    body = r.get_json()
    assert body["success"] is False