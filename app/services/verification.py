from .static_analysis import MAX_CODE_CHARS, analyze_code


def verify_fix(original, corrected):
    """Re-checks the AI's code. Returns a label and an honest note."""
    def suggested(note, remaining=None, checks=None):
        return {"status": "suggested", "note": note,
                "remaining_diagnostics": remaining or [], "checks_run": checks or []}

    if not corrected.strip():
        return suggested("The AI returned empty code.")
    if len(corrected) > MAX_CODE_CHARS:
        return suggested("The corrected code is too long to check.")
    if corrected.strip() == original.strip():
        return suggested("The AI did not change the code, so nothing was fixed or verified.")

    result = analyze_code(corrected)
    if result["diagnostics"]:
        n = len(result["diagnostics"])
        return suggested(str(n) + " problem(s) are still reported in the corrected code.",
                         result["diagnostics"], result["checks_run"])
    if "ruff" not in result["checks_run"]:
        return suggested("Ruff could not run, so only the syntax was checked.",
                         [], result["checks_run"])
    return {
        "status": "statically_verified",
        "note": "Passed the Python syntax check and Ruff. This does not prove the logic is "
                "correct, and no tests were run.",
        "remaining_diagnostics": [],
        "checks_run": result["checks_run"],
    }