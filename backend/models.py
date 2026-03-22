"""
VikeSesh — Database Models
All models use Flask-SQLAlchemy (db.Model) so they integrate cleanly
with Flask, flask-migrate, and the existing extensions.py setup.

The db instance comes from extensions.py — never create a new one here.
"""

from datetime import datetime, timezone
from backend.extensions import db
import enum


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class EventVisibility(enum.Enum):
    PUBLIC_GROUP = "public_group"   # Visible to all group members
    INVITED_ONLY = "invited_only"   # Only explicitly invited members


class InviteStatus(enum.Enum):
    PENDING  = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class MemberRole(enum.Enum):
    OWNER  = "owner"   # Created the group, full control
    ADMIN  = "admin"   # Can edit group and manage members
    MEMBER = "member"  # Standard member


class MessageType(enum.Enum):
    USER   = "user"    # Posted by a student
    SYSTEM = "system"  # Auto-generated (e.g. "[Alice] joined the group")


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────

def utcnow():
    """Use this instead of datetime.utcnow() — returns timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────
# ASSOCIATION TABLES (Many-to-Many)
# ─────────────────────────────────────────────

# Which students are in which groups
group_memberships = db.Table(
    "group_memberships",
    db.Column("student_id", db.Integer, db.ForeignKey("students.id"), primary_key=True),
    db.Column("group_id",   db.Integer, db.ForeignKey("groups.id"),   primary_key=True),
    db.Column("role",       db.Enum(MemberRole), default=MemberRole.MEMBER),
    db.Column("joined_at",  db.DateTime(timezone=True), default=utcnow),
)


# ─────────────────────────────────────────────
# CORE MODELS
# ─────────────────────────────────────────────

class Student(db.Model):
    """
    A UVic student account.
    Merges the auth team's Student model (email, password_hash,
    is_verified, university) with our fuller model (display_name,
    avatar_url, student_number).
    """
    __tablename__ = "students"

    id              = db.Column(db.Integer, primary_key=True)
    email           = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash   = db.Column(db.String(255), nullable=False)
    display_name    = db.Column(db.String(100), nullable=False)
    student_number  = db.Column(db.String(20),  unique=True, nullable=True)
    avatar_url      = db.Column(db.String(500),  nullable=True)   # URL to Cloudinary or local upload
    university      = db.Column(db.String(255),  nullable=True, default="University of Victoria")
    is_verified     = db.Column(db.Boolean, default=False, nullable=False)  # True after OTP verified
    is_active       = db.Column(db.Boolean, default=True,  nullable=False)
    created_at      = db.Column(db.DateTime(timezone=True), default=utcnow)

    # Relationships
    groups         = db.relationship("Group", secondary=group_memberships, back_populates="members")
    created_events = db.relationship("Event", back_populates="creator", foreign_keys="Event.creator_id")
    invitations    = db.relationship("EventInvitation", back_populates="student", foreign_keys="EventInvitation.student_id")

    def __repr__(self):
        return f"<Student {self.display_name} ({self.email})>"


class OTP(db.Model):
    """
    Stores one-time password codes for email verification and password reset.
    Taken directly from the auth team's model — keeping their exact field names
    (code, is_used) so their routes work without changes.

    The code should be stored as a bcrypt hash in production.
    expires_at is set to created_at + 10 minutes by the auth route.
    is_used is set to True once verified to prevent reuse.
    """
    __tablename__ = "otps"

    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(255), nullable=False, index=True)
    code       = db.Column(db.String(6),   nullable=False)   # store bcrypt hash in production
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_used    = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<OTP email={self.email} is_used={self.is_used}>"


class Group(db.Model):
    """
    A group students can join (e.g. 'MATH 100', 'UVic Chess Club').
    Events are scoped to groups.
    parent_group_id enables subgroups e.g. 'MATH 100 — Dr. Smith'
    pointing back to 'MATH 100'.
    """
    __tablename__ = "groups"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    course_code = db.Column(db.String(20), index=True)    # e.g. "MATH100" — null for clubs
    icon_url    = db.Column(db.String(500))
    is_public   = db.Column(db.Boolean, default=True)     # False = invite-only group
    created_at  = db.Column(db.DateTime(timezone=True), default=utcnow)
    created_by  = db.Column(db.Integer, db.ForeignKey("students.id"))

    # Self-referencing for subgroups
    parent_group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    parent_group    = db.relationship("Group", remote_side="Group.id", back_populates="subgroups", foreign_keys=[parent_group_id])
    subgroups       = db.relationship("Group", back_populates="parent_group", foreign_keys=[parent_group_id])

    # Relationships
    members = db.relationship("Student", secondary=group_memberships, back_populates="groups")
    events  = db.relationship("Event", back_populates="group")

    def __repr__(self):
        return f"<Group {self.name}>"


class CampusLocation(db.Model):
    """
    A named spot on campus.
    latitude and longitude place pins on the React Leaflet map.
    """
    __tablename__ = "campus_locations"

    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(200), nullable=False)   # e.g. "Clearihue A110"
    building  = db.Column(db.String(100))
    room      = db.Column(db.String(50))                    # null for outdoor locations
    latitude  = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    # Relationships
    events = db.relationship("Event", back_populates="location")

    def __repr__(self):
        return f"<CampusLocation {self.name}>"


class Event(db.Model):
    """
    An event created within a group.

    visibility controls map pin behaviour:
      PUBLIC_GROUP  — pin shown to all group members automatically
      INVITED_ONLY  — pin only shown to students with an EventInvitation row

    recurrence_rule stores an RFC 5545 RRULE string for recurring events.
    e.g. "FREQ=WEEKLY;BYDAY=TU;COUNT=10" = every Tuesday for 10 weeks.
    Null means the event is a one-time occurrence.
    """
    __tablename__ = "events"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    creator_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    group_id    = db.Column(db.Integer, db.ForeignKey("groups.id"),   nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("campus_locations.id"))

    start_time      = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time        = db.Column(db.DateTime(timezone=True))
    recurrence_rule = db.Column(db.String(500), nullable=True)

    visibility   = db.Column(db.Enum(EventVisibility), default=EventVisibility.PUBLIC_GROUP, nullable=False)
    created_at   = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at   = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    is_cancelled = db.Column(db.Boolean, default=False)

    # Relationships
    creator     = db.relationship("Student", back_populates="created_events", foreign_keys=[creator_id])
    group       = db.relationship("Group", back_populates="events")
    location    = db.relationship("CampusLocation", back_populates="events")
    invitations = db.relationship("EventInvitation", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event '{self.title}'>"


class EventInvitation(db.Model):
    """
    Tracks who has been invited to a specific event.

    PUBLIC_GROUP events: a row is auto-created for every group member.
    INVITED_ONLY events: rows only created for explicitly invited students.

    The map pin query checks for non-declined invitations.
    invited_by is null for system-generated invitations (public events).
    """
    __tablename__ = "event_invitations"

    id           = db.Column(db.Integer, primary_key=True)
    event_id     = db.Column(db.Integer, db.ForeignKey("events.id"),   nullable=False, index=True)
    student_id   = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    invited_by   = db.Column(db.Integer, db.ForeignKey("students.id"))  # null = system-generated
    status       = db.Column(db.Enum(InviteStatus), default=InviteStatus.PENDING, nullable=False)
    invited_at   = db.Column(db.DateTime(timezone=True), default=utcnow)
    responded_at = db.Column(db.DateTime(timezone=True))

    # Relationships
    event   = db.relationship("Event", back_populates="invitations")
    student = db.relationship("Student", back_populates="invitations", foreign_keys=[student_id])
    inviter = db.relationship("Student", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<Invitation event={self.event_id} student={self.student_id} status={self.status}>"


class Message(db.Model):
    """
    A message posted in a group's message board.

    MessageType.SYSTEM rows are auto-created when students join/leave.
    They appear as greyed-out notices in the chat and have no author.
    """
    __tablename__ = "messages"

    id           = db.Column(db.Integer, primary_key=True)
    group_id     = db.Column(db.Integer, db.ForeignKey("groups.id"),   nullable=False, index=True)
    author_id    = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)  # null for system
    content      = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.Enum(MessageType), default=MessageType.USER, nullable=False)
    created_at   = db.Column(db.DateTime(timezone=True), default=utcnow, index=True)
    is_deleted   = db.Column(db.Boolean, default=False)  # soft delete

    # Relationships
    group  = db.relationship("Group",   backref="messages")
    author = db.relationship("Student", backref="messages", foreign_keys=[author_id])

    def __repr__(self):
        return f"<Message group={self.group_id} type={self.message_type.value}>"
