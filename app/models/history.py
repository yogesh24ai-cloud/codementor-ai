from datetime import UTC, datetime

from ..extensions import db


def _now():
    return datetime.now(UTC)


class DebugSession(db.Model):
    __tablename__ = "debug_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    language = db.Column(db.String(20), nullable=False, default="python")
    original_code = db.Column(db.Text, nullable=False)
    diagnostics = db.Column(db.JSON, nullable=False, default=list)
    status = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    result = db.relationship(
        "AIResult", back_populates="session", uselist=False,
        cascade="all, delete-orphan",
    )


class AIResult(db.Model):
    __tablename__ = "ai_results"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("debug_sessions.id"), nullable=False, unique=True
    )
    category = db.Column(db.String(100), nullable=False)
    line = db.Column(db.Integer, nullable=True)
    root_cause = db.Column(db.Text, nullable=False)
    beginner_explanation = db.Column(db.Text, nullable=False)
    why_fix_works = db.Column(db.Text, nullable=False)
    prevention_tips = db.Column(db.JSON, nullable=False, default=list)
    corrected_code = db.Column(db.Text, nullable=False)
    changes_summary = db.Column(db.JSON, nullable=False, default=list)
    verification_status = db.Column(db.String(30), nullable=False)
    verification_note = db.Column(db.Text, nullable=False, default="")
    model_name = db.Column(db.String(100), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    session = db.relationship("DebugSession", back_populates="result")