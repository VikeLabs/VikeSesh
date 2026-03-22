"""
VikeSesh — Flask Extensions
Centralizes the SQLAlchemy db instance so it can be imported
by models.py, routes, and anywhere else without circular imports.

Every model file does:
    from backend.extensions import db

Every route file does:
    from backend.extensions import db
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
