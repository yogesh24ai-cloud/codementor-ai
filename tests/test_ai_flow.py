import json

import pytest

from app.services.schemas import AIResponseError, parse_ai_response
from app.services.verification import verify_fix

GOOD = {
    "category": "SyntaxError", "line": 1, "root_cause": "Missing colon.",
    "beginner_explanation": "def lines end with a colon.", "why_fix_works": "Colon starts the block.",
    "prevention_tips": ["End def lines with a colon."], "changes": ["Line 1: added ':'"],
    "corrected_code": "def f():\n    return 1\n", "verification_recommendations": ["Call f()."],
}


class FakeAI:
    model_name = "fake"

    def __init__(self, reply):
        self.reply = reply

    def generate(self, system, user):
        return self.reply


def test_parse_accepts_json_inside_fences():
    fix = parse_ai_response("```json\n" + json.dumps(GOOD) + "\n```")
    assert fix.line == 1


def test_parse_rejects_garbage():
    with pytest.raises(AIResponseError):
        parse_ai_response("sorry, I cannot help")


def test_parse_rejects_missing_fields():
    with pytest.raises(AIResponseError):
        parse_ai_response(json.dumps({"category": "x"}))


def test_good_fix_is_statically_verified():
    assert verify_fix("def f()\n    return 1\n", GOOD["corrected_code"])["status"] == "statically_verified"


def test_broken_fix_stays_suggested():
    assert verify_fix("def f()\n    return 1\n", "def f()\n    return 1\n!!")["status"] == "suggested"


def test_unchanged_code_is_not_verified():
    assert verify_fix("x = 1\n", "x = 1\n")["status"] == "suggested"


def test_debug_endpoint_with_fake_ai(client, monkeypatch):
    monkeypatch.setattr("app.routes.api.get_ai_client", lambda: FakeAI(json.dumps(GOOD)))
    res = client.post("/api/debug", json={"code": "def f()\n    return 1\n", "language": "python"})
    body = res.get_json()
    assert res.status_code == 200
    assert body["verification"]["status"] == "statically_verified"


def test_debug_endpoint_rejects_bad_ai_output(client, monkeypatch):
    monkeypatch.setattr("app.routes.api.get_ai_client", lambda: FakeAI("not json"))
    res = client.post("/api/debug", json={"code": "x = 1", "language": "python"})
    assert res.status_code == 502


def test_missing_key_gives_503(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    res = client.post("/api/debug", json={"code": "x = 1", "language": "python"})
    assert res.status_code == 503