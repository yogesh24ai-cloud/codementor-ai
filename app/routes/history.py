from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.history import DebugSession

history_bp = Blueprint("history", __name__, url_prefix="/history")


def _own_or_404(session_id):
    """Only the owner can open an entry. Others get a 404."""
    entry = db.session.execute(
        db.select(DebugSession).filter_by(id=session_id, user_id=current_user.id)
    ).scalar_one_or_none()
    if entry is None:
        abort(404)
    return entry


@history_bp.get("/")
@login_required
def list_page():
    rows = db.session.execute(
        db.select(DebugSession)
        .filter_by(user_id=current_user.id)
        .order_by(DebugSession.created_at.desc())
        .limit(50)
    ).scalars().all()
    return render_template("history.html", rows=rows)


@history_bp.get("/<int:session_id>")
@login_required
def detail(session_id):
    return render_template("history_detail.html", entry=_own_or_404(session_id))


@history_bp.post("/<int:session_id>/delete")
@login_required
def delete(session_id):
    entry = _own_or_404(session_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("history.list_page"))