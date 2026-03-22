"""
VikeSesh — Database Setup
Handles the SQLAlchemy engine, session, and table creation.
All other files import get_db() from here to access the database.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Read DATABASE_URL from environment variable.
# Falls back to a local SQLite file for development if not set.
# In production this will be: postgresql://user:password@host/vikesesh
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vikesesh_test.db")

engine = create_engine(
    DATABASE_URL,
    # SQLite needs this extra arg to work across threads in Flask.
    # Has no effect on PostgreSQL so it's safe to leave in always.
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine)


def get_db():
    """
    Returns a database session.
    Always call db.close() when done — use a try/finally block.

    Usage in a Flask route:
        db = get_db()
        try:
            students = db.query(Student).all()
        finally:
            db.close()
    """
    return SessionLocal()


def init_db():
    """
    Creates all tables if they don't exist.
    Called once when the Flask app starts.
    Does NOT drop existing tables — use seed.py for that during development.
    """
    Base.metadata.create_all(engine)
