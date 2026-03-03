import os
from flask import Flask
from backend.extensions import db, migrate

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///vikesesh.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so migrate can detect them
    from backend import models  # noqa: F401

    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    return app