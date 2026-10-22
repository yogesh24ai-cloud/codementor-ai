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