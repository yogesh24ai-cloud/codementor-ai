import json
from datetime import datetime, timedelta

GOOD = {
    "category": "SyntaxError", "line": 1, "root_cause": "Missing colon.",
    "beginner_explanation": "def lines end with a colon.", "why_fix_works": "Colon starts the block.",
    "prevention_tips": ["End def lines with a colon."], "changes": ["Line 1: added ':'"],
    "corrected_code": "def f():\n    return 1\n", "verification_recommendations": ["Call f()."],
}
CODE = "def f()\n    return 1\n"


class FakeAI:
    model_name = "fake"

    def generate(self, system, user):
        return json.dumps(GOOD)


def make_user(app, email):
    c = app.test_client()
    c.post("/register", data={"email": email, "password": "password123"})
    return c


def run_debug(client):
    return client.post("/api/debug", json={"code": CODE, "language": "python"})


def test_anonymous_result_is_not_saved_and_history_needs_login(client, monkeypatch):
    monkeypatch.setattr("app.routes.api.get_ai_client", lambda: FakeAI())
    body = run_debug(client).get_json()
    assert body["saved_id"] is None and body["logged_in"] is False
    assert client.get("/history/").status_code == 302


def test_logged_in_result_is_saved_and_listed(app, monkeypatch):
    monkeypatch.setattr("app.routes.api.get_ai_client", lambda: FakeAI())
    c = make_user(app, "a@b.com")
    saved_id = run_debug(c).get_json()["saved_id"]
    assert saved_id is not None
    assert b"SyntaxError" in c.get("/history/").data
    detail = c.get(f"/history/{saved_id}")
    assert detail.status_code == 200
    assert b"Missing colon." in detail.data


def test_other_users_cannot_open_an_entry(app, monkeypatch):
    monkeypatch.setattr("app.routes.api.get_ai_client", lambda: FakeAI())
    owner = make_user(app, "owner@b.com")
    saved_id = run_debug(owner).get_json()["saved_id"]
    other = make_user(app, "other@b.com")
    assert other.get(f"/history/{saved_id}").status_code == 404
    assert other.post(f"/history/{saved_id}/delete").status_code == 404


def test_delete_removes_entry(app, monkeypatch):
    monkeypatch.setattr("app.routes.api.get_ai_client", lambda: FakeAI())
    c = make_user(app, "a@b.com")
    saved_id = run_debug(c).get_json()["saved_id"]
    assert c.post(f"/history/{saved_id}/delete").status_code == 302
    assert c.get(f"/history/{saved_id}").status_code == 404


def test_save_failure_does_not_break_the_result(app, monkeypatch):
    monkeypatch.setattr("app.routes.api.get_ai_client", lambda: FakeAI())
    c = make_user(app, "a@b.com")

    def boom():
        raise RuntimeError("database down")

    monkeypatch.setattr("app.routes.api.db.session.commit", boom)
    res = run_debug(c)
    assert res.status_code == 200
    assert res.get_json()["saved_id"] is None
    assert res.get_json()["fix"]["category"] == "SyntaxError"


def test_progress_compares_recent_reviews_for_the_logged_in_user(app):
    from app.extensions import db
    from app.models.history import DebugSession
    from app.models.user import User

    client = make_user(app, "progress@b.com")
    with app.app_context():
        user_id = db.session.execute(
            db.select(User.id).filter_by(email="progress@b.com")
        ).scalar_one()
        for index, error_count in enumerate((4, 4, 2, 2)):
            db.session.add(DebugSession(
                user_id=user_id,
                original_code="pass",
                diagnostics=[{"rule": "F821"}] * error_count,
                status="suggested",
                created_at=datetime(2026, 1, 1) + timedelta(minutes=index),
            ))
        db.session.commit()

    data = client.get("/api/progress").get_json()
    assert data["total_analyses"] == 4
    assert data["latest_errors"] == 2
    assert data["trend"] == "improved"
    assert data["change_percent"] == 50
    assert data["history"] == [2, 2, 4, 4]


def test_progress_only_includes_the_current_users_history(app):
    from app.extensions import db
    from app.models.history import DebugSession
    from app.models.user import User
    client = make_user(app, "empty@b.com")
    with app.app_context():
        owner = User(email="someone-else@b.com", password_hash="unused")
        db.session.add(owner)
        db.session.flush()
        db.session.add(DebugSession(
            user_id=owner.id,
            original_code="pass",
            diagnostics=[{"rule": "F821"}] * 8,
            status="suggested",
        ))
        db.session.commit()

    data = client.get("/api/progress").get_json()
    assert data["total_analyses"] == 0
    assert data["history"] == []
