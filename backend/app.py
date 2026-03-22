"""
VikeSesh — Flask Application Entry Point

Run locally:
    python -m backend.app
    OR
    flask --app backend.app run --debug

The app uses Flask-SQLAlchemy and flask-migrate so database changes
are tracked with Alembic migrations in the /migrations folder.
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from backend.extensions import db

# Import all blueprints
from backend.routes.groups   import groups_bp
from backend.routes.events   import events_bp
from backend.routes.messages import messages_bp
from backend.routes.map      import map_bp


def create_app():
    """
    Application factory pattern — creates and configures the Flask app.
    Using a factory makes the app easier to test and configure for
    different environments (dev, test, production).
    """
    app = Flask(__name__)

    # ── Configuration ─────────────────────────────────────────
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///vikesesh.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")

    # ── Extensions ────────────────────────────────────────────
    db.init_app(app)
    Migrate(app, db)  # enables 'flask db migrate' and 'flask db upgrade' commands

    # CORS: allows the Next.js frontend (port 3000) to call this API (port 5000)
    # In production replace "*" with your actual frontend domain
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Blueprints ────────────────────────────────────────────
    app.register_blueprint(groups_bp,   url_prefix="/api")
    app.register_blueprint(events_bp,   url_prefix="/api")
    app.register_blueprint(messages_bp, url_prefix="/api")
    app.register_blueprint(map_bp,      url_prefix="/api")

    # ── JSON Error Handlers ───────────────────────────────────
    # Replaces Flask's HTML error pages with JSON so Next.js
    # can always parse the response regardless of status code.

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"data": None, "error": "Bad request"}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"data": None, "error": "Unauthorized — please log in"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"data": None, "error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"data": None, "error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"data": None, "error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"data": None, "error": "Internal server error"}), 500

    return app


# ── Entry point ───────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    print("✅ VikeSesh backend running at http://localhost:5000")
    print("   Run 'flask db upgrade' to apply migrations before starting.")
    app.run(debug=True, port=5000)
