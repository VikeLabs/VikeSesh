"""
VikeSesh — Flask Application Entry Point
Run locally with:  python app.py
Run with Flask CLI: flask run
"""

from flask import Flask
from database import init_db

# Import all blueprints
from routes.groups   import groups_bp
from routes.events   import events_bp
from routes.messages import messages_bp
from routes.map      import map_bp

app = Flask(__name__)

# ── Register Blueprints ───────────────────────────────────────
# All routes are prefixed with /api so the frontend always calls
# http://localhost:5000/api/...
app.register_blueprint(groups_bp,   url_prefix="/api")
app.register_blueprint(events_bp,   url_prefix="/api")
app.register_blueprint(messages_bp, url_prefix="/api")
app.register_blueprint(map_bp,      url_prefix="/api")

# ── Standard JSON Error Handlers ─────────────────────────────
# These replace Flask's default HTML error pages with JSON so the
# Next.js frontend can always parse the response.
from flask import jsonify

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"data": None, "error": "Bad request"}), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"data": None, "error": "Unauthorized — please log in"}), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"data": None, "error": "Forbidden — you don't have permission"}), 403

@app.errorhandler(404)
def not_found(e):
    return jsonify({"data": None, "error": "Not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"data": None, "error": "Method not allowed"}), 405

@app.errorhandler(500)
def server_error(e):
    return jsonify({"data": None, "error": "Internal server error"}), 500


# ── Startup ───────────────────────────────────────────────────
if __name__ == "__main__":
    # Create tables if they don't exist yet
    init_db()
    print("✅ VikeSesh Flask backend running at http://localhost:5000")
    print("   Endpoints:")
    print("   GET  /api/groups")
    print("   POST /api/groups")
    print("   GET  /api/groups/<id>")
    print("   POST /api/groups/<id>/join")
    print("   DEL  /api/groups/<id>/leave")
    print("   GET  /api/groups/<id>/events")
    print("   POST /api/groups/<id>/events")
    print("   POST /api/events/<id>/respond")
    print("   PATC /api/events/<id>")
    print("   DEL  /api/events/<id>")
    print("   GET  /api/groups/<id>/messages")
    print("   POST /api/groups/<id>/messages")
    print("   GET  /api/map-pins/<student_id>")
    app.run(debug=True, port=5000)
