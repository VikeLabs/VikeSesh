from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Association Table for Many-to-Many relationship
class Membership(db.Model):
    __tablename__ = 'memberships'
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), primary_key=True)
    
    # Role: 1=Member, 2=Manager, 3=Owner
    role = db.Column(db.Integer, default=1)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False) # Must end in @uvic.ca
    display_name = db.Column(db.String(80), nullable=False)
    
    # Link to groups through the membership table
    groups = db.relationship('Membership', backref='student', lazy=True)

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(20)) # e.g., "CSC 230"
    is_private = db.Column(db.Boolean, default=False)
    
    members = db.relationship('Membership', backref='group', cascade="all, delete-orphan")
    events = db.relationship('Event', backref='group', lazy=True)