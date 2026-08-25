"""Analytics and history page tests."""
from app import db
from app.models.analysis import Analysis
from app.models.user import User


def _add_analyses(app, username, items):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        for label, conf in items:
            db.session.add(Analysis(
                user_id=user.id, image_filename=f"{label}.png",
                label=label, confidence=conf, food_type="fruit",
            ))
        db.session.commit()


def test_history_lists_own_records(app, client):
    client.post("/auth/register", data={"username": "hist", "email": "h@x.com",
                                        "password": "password123"})
    client.post("/auth/login", data={"username": "hist", "password": "password123"})
    _add_analyses(app, "hist", [("Fresh", 0.92), ("Avoid", 0.55)])

    r = client.get("/history")
    assert r.status_code == 200
    assert b"Fresh" in r.data
    assert b"Avoid" in r.data


def test_history_label_filter(client, app):
    client.post("/auth/register", data={"username": "filt", "email": "f@x.com",
                                        "password": "password123"})
    client.post("/auth/login", data={"username": "filt", "password": "password123"})
    _add_analyses(app, "filt", [("Fresh", 0.9), ("Okay", 0.6)])

    r = client.get("/history?label=Avoid")
    assert r.status_code == 200
    # No Avoid records exist -> the table body is empty / empty state shown
    assert b"No analyses yet" in r.data


def test_analytics_kpis(app, client):
    client.post("/auth/register", data={"username": "stats", "email": "s@x.com",
                                        "password": "password123"})
    client.post("/auth/login", data={"username": "stats", "password": "password123"})
    _add_analyses(app, "stats", [("Fresh", 0.9), ("Fresh", 0.8),
                                 ("Okay", 0.6), ("Avoid", 0.4)])

    r = client.get("/analytics")
    assert r.status_code == 200
    html = r.data.decode()
    assert "Total Analyses" in html
    assert ">2<" in html          # fresh count
    assert ">1<" in html          # okay / avoid counts


def test_analytics_empty_state(client):
    client.post("/auth/register", data={"username": "empty", "email": "e@x.com",
                                        "password": "password123"})
    client.post("/auth/login", data={"username": "empty", "password": "password123"})
    r = client.get("/analytics")
    assert r.status_code == 200
    assert b"No analyses yet" in r.data