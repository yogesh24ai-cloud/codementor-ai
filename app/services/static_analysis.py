import ast
import json
import subprocess
import sys

MAX_CODE_CHARS = 50_000
RUFF_TIMEOUT_SECONDS = 10


def _category_for(rule):
    if rule.startswith("E9"):
        return "Syntax error"
    if rule.startswith(("F", "PL")):
        return "Possible bug"
    if rule.startswith("B"):
        return "Risky code pattern"
    return "Style or other"


def check_syntax(code):
    """Reads the code with Python's parser. Never runs it."""
    try:
        ast.parse(code)
        return []
    except SyntaxError as e:
        return [{
            "source": "python-ast",
            "rule": "SyntaxError",
            "category": "Syntax error",
            "line": e.lineno,
            "column": e.offset,
            "message": e.msg or "Invalid syntax",
        }]
    except (ValueError, RecursionError, MemoryError) as e:
        return [{
            "source": "python-ast",
            "rule": "ParseError",
            "category": "Syntax error",
            "line": None,
            "column": None,
            "message": "The code could not be parsed: " + str(e)[:150],
        }]


def run_ruff(code):
    """Runs Ruff as a separate process. Returns (diagnostics, note)."""
    cmd = [
        sys.executable, "-m", "ruff", "check",
        "--isolated", "--no-cache",
        "--select", "E9,F,B,PLE,PLW",
        "--output-format", "json",
        "--stdin-filename", "code.py",
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd, input=code, capture_output=True, text=True,
            encoding="utf-8", timeout=RUFF_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired:
        return [], "Ruff took too long and was stopped."
    except OSError:
        return [], "Ruff could not be started. Is it installed?"

    if proc.returncode not in (0, 1):
        return [], "Ruff failed: " + proc.stderr.strip()[:200]

    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return [], "Ruff returned output that could not be read."

    results = []
    for item in items:
        rule = item.get("code") or "SyntaxError"
        location = item.get("location") or {}
        results.append({
            "source": "ruff",
            "rule": rule,
            "category": _category_for(rule),
            "line": location.get("row"),
            "column": location.get("column"),
            "message": item.get("message", ""),
        })
    return results, None


def analyze_code(code):
    notes = []
    syntax_problems = check_syntax(code)
    if syntax_problems:
        notes.append("Fix the syntax error first. Ruff's other checks run once the code parses.")
        return {"diagnostics": syntax_problems,
                "checks_run": ["python-ast"], "notes": notes,
                "scope": "Static checks find common bug patterns; they do not prove logic is correct."}

    diagnostics, ruff_note = run_ruff(code)
    checks = ["python-ast"]
    if ruff_note:
        notes.append(ruff_note)
    else:
        checks.append("ruff")
    diagnostics.sort(key=lambda d: (d["line"] or 0))
    return {
        "diagnostics": diagnostics,
        "checks_run": checks,
        "notes": notes,
        "scope": "Static checks find common bug patterns; they do not prove logic is correct.",
    }