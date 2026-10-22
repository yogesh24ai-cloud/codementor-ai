import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user

from ..extensions import db, limiter
from ..models.history import AIResult, DebugSession
from ..services.ai_clients import AIConfigError, AIServiceError, get_ai_client
from ..services.prompts import SYSTEM_PROMPT, build_user_prompt
from ..services.schemas import AIResponseError, parse_ai_response
from ..services.static_analysis import MAX_CODE_CHARS, analyze_code
from ..services.verification import verify_fix

log = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")


def _read_code():
    """Returns (code, error_response)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify(error="Send JSON with a 'code' field."), 400)
    code = data.get("code")
    if data.get("language", "python") != "python":
        return None, (jsonify(error="Only Python is supported right now."), 400)
    if not isinstance(code, str) or not code.strip():
        return None, (jsonify(error="No code was provided."), 400)
    if len(code) > MAX_CODE_CHARS:
        return None, (jsonify(error="Code is too long (limit: 50,000 characters)."), 413)
    return code, None


def _save_history(code, analysis, fix, verification, model_name):
    """Saves the result for the logged-in user. Never breaks the response."""
    try:
        entry = DebugSession(
            user_id=current_user.id,
            language="python",
            original_code=code,
            diagnostics=analysis["diagnostics"],
            status=verification["status"],
        )
        entry.result = AIResult(
            category=fix.category,
            line=fix.line,
            root_cause=fix.root_cause,
            beginner_explanation=fix.beginner_explanation,
            why_fix_works=fix.why_fix_works,
            prevention_tips=fix.prevention_tips + fix.verification_recommendations,
            corrected_code=fix.corrected_code,
            changes_summary=fix.changes,
            verification_status=verification["status"],
            verification_note=verification["note"],
            model_name=model_name,
        )
        db.session.add(entry)
        db.session.commit()
        return entry.id
    except Exception:
        db.session.rollback()
        log.exception("Could not save history")
        return None


@api_bp.post("/analyze")
def analyze():
    code, err = _read_code()
    if err:
        return err
    return jsonify(analyze_code(code))


@api_bp.post("/debug")
@limiter.limit("3 per minute;20 per hour")
def debug():
    code, err = _read_code()
    if err:
        return err

    analysis = analyze_code(code)
    try:
        client = get_ai_client()
    except AIConfigError as e:
        return jsonify(error=str(e)), 503

    prompt = build_user_prompt(code, analysis["diagnostics"])
    fix = None
    for _ in range(2):  # one retry if the answer is unusable
        try:
            raw = client.generate(SYSTEM_PROMPT, prompt)
        except AIServiceError as e:
            return jsonify(error=str(e)), 502
        try:
            fix = parse_ai_response(raw)
            break
        except AIResponseError:
            continue
    if fix is None:
        return jsonify(error="The AI gave an unusable answer. Please try again."), 502

    verification = verify_fix(code, fix.corrected_code)
    saved_id = None
    if current_user.is_authenticated:
        saved_id = _save_history(code, analysis, fix, verification, client.model_name)

    return jsonify(
        analysis=analysis,
        fix=fix.model_dump(),
        verification=verification,
        model=client.model_name,
        logged_in=current_user.is_authenticated,
        saved_id=saved_id,
    )