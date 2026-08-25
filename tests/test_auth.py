"""Authentication tests: registration, login, hashing, logout, isolation."""
from app import db
from app.models.user import User


def _register(client, username="alice", email="a@x.com", password="secret123"):
    return client.post(
        "/auth/register",
        data={"username": username, "email": email, "password": password},
    )


def test_registration_succeeds(client):
    r = _register(client)
    assert r.status_code == 200
    assert b"Registration successful" in r.data


def test_registration_duplicate_username(client):
    _register(client, username="bob")
    r = _register(client, username="bob", email="other@x.com")
    assert b"Username already taken" in r.data


def test_registration_short_password_rejected(client):
    r = _register(client, username="carol", password="short")
    assert r.status_code == 200  # re-renders form
    assert b"Registration successful" not in r.data


def test_password_is_hashed_not_plaintext(app):
    from conftest import make_image  # noqa: F401  (keeps imports stable)

    with app.app_context():
        user = User(username="hashcheck", email="h@x.com")
        user.set_password("mypassword")
        db.session.add(user)
        db.session.commit()
        stored = User.query.filter_by(username="hashcheck").first()
        assert stored.password_hash != "mypassword"
        assert stored.password_hash.startswith("pbkdf2:")
        assert stored.check_password("mypassword")
        assert not stored.check_password("wrong")


def test_login_success_redirects_to_dashboard(client):
    _register(client)
    r = client.post("/auth/login", data={"username": "alice", "password": "secret123"})
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_login_wrong_password_fails(client):
    _register(client)
    r = client.post("/auth/login", data={"username": "alice", "password": "wrongpass"})
    assert b"Invalid username or password" in r.data


def test_logout(client):
    _register(client)
    client.post("/auth/login", data={"username": "alice", "password": "secret123"})
    r = client.get("/logout")
    assert r.status_code == 302
    # After logout, protected pages redirect to login
    r = client.get("/dashboard")
    assert r.status_code == 302


def test_protected_pages_require_login(client):
    for path in ("/dashboard", "/history", "/analytics", "/profile"):
        r = client.get(path)
        assert r.status_code == 302, f"{path} should require login"


def test_user_isolation(app, client):
    """User B cannot view user A's analysis."""
    from app.models.analysis import Analysis

    _register(client, username="owner", email="o@x.com")
    client.post("/auth/login", data={"username": "owner", "password": "secret123"})
    with app.app_context():
        owner = User.query.filter_by(username="owner").first()
        analysis = Analysis(user_id=owner.id, image_filename="x.png",
                            label="Fresh", confidence=0.9)
        db.session.add(analysis)
        db.session.commit()
        analysis_id = analysis.id

    # Second user tries to access it
    c2 = app.test_client()
    _register(c2, username="intruder", email="i@x.com")
    c2.post("/auth/login", data={"username": "intruder", "password": "secret123"})
    r = c2.get(f"/result/{analysis_id}")
    assert r.status_code == 302  # redirected away, not shown

    # API returns 403
    r = c2.get(f"/api/v1/analysis/{analysis_id}")
    assert r.status_code == 403