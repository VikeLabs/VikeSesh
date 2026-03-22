from flask import Flask
from flask_cors import CORS
from models import db
from routes.groups import groups_bp
import os

app = Flask(__name__)
CORS(app) # Allows your Next.js frontend to talk to this API

# Database configuration (using local SQLite for now to keep it easy)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vikesesh.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Register the routes from groups.py
app.register_blueprint(groups_bp)

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)