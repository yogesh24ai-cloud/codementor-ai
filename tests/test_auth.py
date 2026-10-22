from app.extensions import db
from app.models.user import User

CREDS = {"email": "a@b.com", "password": "password123"}


def register(client, **overrides):
    return client.post("/register", data={**CREDS, **overrides}, follow_redirects=True)


def test_register_logs_user_in(client):
    res = register(client)
    assert res.status_code == 200
    assert b"a@b.com" in res.data
    assert b"Log out" in res.data


def test_duplicate_email_rejected(client):
    register(client)
    client.post("/logout")
    res = register(client)
    assert b"already registered" in res.data


def test_short_password_rejected(client):
    res = register(client, password="short")
    assert b"8 to 128" in res.data


def test_wrong_password_rejected(client):
    register(client)
    client.post("/logout")
    res = client.post("/login", data={**CREDS, "password": "wrong-password"})
    assert b"Wrong email or password" in res.data


def test_correct_login_works(client):
    register(client)
    client.post("/logout")
    res = client.post("/login", data=CREDS, follow_redirects=True)
    assert b"Log out" in res.data


def test_password_is_stored_hashed(app, client):
    register(client)
    with app.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        assert user.password_hash != CREDS["password"]
        assert CREDS["password"] not in user.password_hash


def test_logout_needs_post(client):
    register(client)
    assert client.get("/logout").status_code == 405
    res = client.post("/logout", follow_redirects=True)
    assert b"Log in" in res.data