"""Single application factory. Startup never creates or recreates database tables."""

import fcntl
import os
import posixpath
import secrets
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from sqlalchemy.exc import IntegrityError, OperationalError

from config import Config
from extensions import csrf, db, login_manager


def create_app(test_config=None):
    app = Flask(__name__, instance_path=os.environ.get("STOCKPILOT_INSTANCE"))
    app.config.from_object(Config)
    app.config.update(test_config or {})
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        # A persistent random local secret works across restarts and worker processes.
        path = Path(app.instance_path) / "secret-key"
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, "r+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            secret = stream.read().strip()
            if not secret:
                secret = secrets.token_hex(32)
                stream.write(secret)
                stream.flush()
            app.config["SECRET_KEY"] = secret
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    from account import bp as account_bp
    from api import bp as api_bp
    from auth import bp as auth_bp
    from commands import register_commands
    from main import bp as main_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(account_bp, url_prefix="/profile")
    app.register_blueprint(api_bp, url_prefix="/api")
    csrf.exempt(api_bp)  # API exclusively uses bearer tokens, never session cookies.
    register_commands(app)

    @app.before_request
    def protect_legacy_uploads():
        filename = posixpath.normpath((request.view_args or {}).get("filename", ""))
        if request.endpoint == "static" and filename.startswith("uploads/"):
            from main import uploaded_image

            return uploaded_image(filename.removeprefix("uploads/"))

    from services.inventory import InventoryError

    @app.errorhandler(InventoryError)
    def invalid_inventory(error):
        db.session.rollback()
        return render_template("error.html", code=400, message=str(error)), 400

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        db.session.rollback()
        if request.path.startswith("/api/"):
            return jsonify(error="The record conflicts with existing data."), 409
        return render_template(
            "error.html", code=409, message="The record conflicts with existing data."
        ), 409

    @app.errorhandler(OperationalError)
    def database_error(error):
        db.session.rollback()
        app.logger.error("Database unavailable: %s", type(error).__name__)
        if request.path.startswith("/api/"):
            return jsonify(error="Database unavailable. Run flask --app app init-db."), 503
        return render_template(
            "error.html",
            code=503,
            message="Database unavailable. Run flask --app app init-db, or retry shortly.",
        ), 503

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("error.html", code=500, message="Unable to complete this request."), 500

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return render_template("error.html", code=error.code, message=error.description), error.code

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.get("/health")
    def health():
        return {"status": "ok", "application": "StockPilot AI"}

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
