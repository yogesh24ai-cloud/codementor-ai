import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_wtf.csrf import CSRFError

from .extensions import csrf, db, limiter, login_manager


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///codementor.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if test_config:
        app.config.update(test_config)

    secret = app.config["SECRET_KEY"]
    if not app.config.get("TESTING") and (not secret or secret == "change-me"):
        raise RuntimeError(
            "SECRET_KEY is missing or still 'change-me'. Set a long random value in .env."
        )

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from . import models  # noqa: F401
    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.history import history_bp
    from .routes.pages import pages_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)

    with app.app_context():
        db.create_all()

    @app.errorhandler(429)
    def too_many(e):
        return jsonify(error="Too many requests. Please wait a minute and try again."), 429

    @app.errorhandler(413)
    def too_large(e):
        return jsonify(error="The request is too large."), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify(error="Something went wrong on the server. Please try again."), 500

    @app.errorhandler(CSRFError)
    def csrf_failed(e):
        return jsonify(error="Your session expired. Refresh the page and try again."), 400

    @app.after_request
    def add_security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    return app