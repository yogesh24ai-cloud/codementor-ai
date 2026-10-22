from app.services.static_analysis import analyze_code


def test_valid_code_has_no_problems():
    result = analyze_code("x = 1\nprint(x)\n")
    assert result["diagnostics"] == []


def test_missing_colon_is_a_syntax_error_on_line_1():
    result = analyze_code("def f()\n    return 1\n")
    first = result["diagnostics"][0]
    assert first["category"] == "Syntax error"
    assert first["line"] == 1


def test_undefined_name_is_reported_by_ruff():
    result = analyze_code("print(y)\n")
    rules = [d["rule"] for d in result["diagnostics"]]
    assert "F821" in rules


def test_risky_mutable_default_is_reported_as_a_bug_pattern():
    result = analyze_code("def add(item, items=[]):\n    items.append(item)\n    return items\n")
    diagnostic = next(d for d in result["diagnostics"] if d["rule"] == "B006")
    assert diagnostic["category"] == "Risky code pattern"
    assert diagnostic["line"] == 1


def test_analysis_scope_explains_static_logic_check_limits():
    result = analyze_code("print(missing_name)\n")
    assert "common bug patterns" in result["scope"]


def test_api_rejects_empty_code(client):
    res = client.post("/api/analyze", json={"code": "   ", "language": "python"})
    assert res.status_code == 400


def test_api_rejects_other_languages(client):
    res = client.post("/api/analyze", json={"code": "x=1", "language": "java"})
    assert res.status_code == 400


def test_api_analyzes_code(client):
    res = client.post("/api/analyze", json={"code": "print(y)\n", "language": "python"})
    assert res.status_code == 200
    assert res.get_json()["diagnostics"]


def test_progress_requires_login(client):
    assert client.get("/api/progress").status_code == 401