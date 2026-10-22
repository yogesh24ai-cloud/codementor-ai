import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db, limiter
from ..models.user import User

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pages.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(email) > 254 or not EMAIL_RE.match(email):
            flash("Enter a valid email address.")
        elif not 8 <= len(password) <= 128:
            flash("Password must be 8 to 128 characters.")
        else:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("That email is already registered.")
            else:
                login_user(user)
                return redirect(url_for("pages.index"))
    return render_template("auth.html", mode="register")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.execute(
            db.select(User).filter_by(email=email)
        ).scalar_one_or_none()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("pages.index"))
        flash("Wrong email or password.")
    return render_template("auth.html", mode="login")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("pages.index"))