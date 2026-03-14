# backend/seed.py
from app import app
from models import db, Group

with app.app_context():
    # Add a sample group
    csc_group = Group(name="CSC 225", course_code="CSC225", is_private=False)
    
    db.session.add(csc_group)
    db.session.commit()
    print("Database seeded with CSC 225!")