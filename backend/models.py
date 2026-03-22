from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, Float, ForeignKey, Enum, Table
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

# Convenience function — use everywhere instead of datetime.utcnow()
def utcnow():
    return datetime.now(timezone.utc)


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
# ASSOCIATION TABLES (Many-to-Many)
# ─────────────────────────────────────────────

# Which students are in which groups
group_memberships = Table(
    "group_memberships",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id"), primary_key=True),
    Column("group_id",   Integer, ForeignKey("groups.id"),   primary_key=True),
    Column("role",       Enum(MemberRole), default=MemberRole.MEMBER),
    Column("joined_at",  DateTime(timezone=True), default=utcnow),
)


# ─────────────────────────────────────────────
# CORE MODELS
# ─────────────────────────────────────────────

class Student(Base):
    """A UVic student account."""
    __tablename__ = "students"

    id             = Column(Integer, primary_key=True, index=True)
    uvic_email     = Column(String(255), unique=True, nullable=False, index=True)
    display_name   = Column(String(100), nullable=False)
    student_number = Column(String(20), unique=True)
    avatar_url     = Column(String(500))         # URL to Cloudinary or local upload
    created_at     = Column(DateTime(timezone=True), default=utcnow)
    is_active      = Column(Boolean, default=True)

    # Relationships
    groups         = relationship("Group", secondary=group_memberships, back_populates="members")
    created_events = relationship("Event", back_populates="creator", foreign_keys="Event.creator_id")
    invitations    = relationship("EventInvitation", back_populates="student", foreign_keys="EventInvitation.student_id")

    def __repr__(self):
        return f"<Student {self.display_name} ({self.uvic_email})>"


class Group(Base):
    """
    A group students can join (e.g. 'MATH 100', 'UVic Chess Club').
    Events are scoped to groups.
    parent_group_id is null for top-level groups and set for subgroups
    e.g. 'MATH 100 - Dr. Smith' has parent_group_id pointing to 'MATH 100'.
    """
    __tablename__ = "groups"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150), nullable=False)
    description = Column(Text)
    course_code = Column(String(20), index=True)   # e.g. "MATH100" — null for clubs
    icon_url    = Column(String(500))
    is_public   = Column(Boolean, default=True)    # False = invite-only group
    created_at  = Column(DateTime(timezone=True), default=utcnow)
    created_by  = Column(Integer, ForeignKey("students.id"))

    # Self-referencing foreign key for subgroups
    parent_group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    parent_group    = relationship("Group", remote_side=lambda: [Group.id], back_populates="subgroups")
    subgroups       = relationship("Group", back_populates="parent_group")

    # Relationships
    members = relationship("Student", secondary=group_memberships, back_populates="groups")
    events  = relationship("Event", back_populates="group")

    def __repr__(self):
        return f"<Group {self.name}>"


class CampusLocation(Base):
    """
    A named spot on campus (building, courtyard, etc.).
    latitude and longitude are used to place pins on the React Leaflet map.
    """
    __tablename__ = "campus_locations"

    id        = Column(Integer, primary_key=True, index=True)
    name      = Column(String(200), nullable=False)   # e.g. "Clearihue A110"
    building  = Column(String(100))                   # e.g. "Clearihue"
    room      = Column(String(50))                    # e.g. "A110" — null for outdoor locations
    latitude  = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Relationships
    events = relationship("Event", back_populates="location")

    def __repr__(self):
        return f"<CampusLocation {self.name}>"


class Event(Base):
    """
    An event created within a group.

    visibility controls map pin behaviour:
      PUBLIC_GROUP  — pin shown to all group members automatically
      INVITED_ONLY  — pin only shown to students with an EventInvitation row

    recurrence_rule stores an RFC 5545 RRULE string for recurring events.
    e.g. "FREQ=WEEKLY;BYDAY=TU;COUNT=10" means every Tuesday for 10 weeks.
    Null means the event is a one-time occurrence.
    """
    __tablename__ = "events"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text)
    creator_id  = Column(Integer, ForeignKey("students.id"), nullable=False)
    group_id    = Column(Integer, ForeignKey("groups.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("campus_locations.id"))

    # Scheduling
    start_time      = Column(DateTime(timezone=True), nullable=False)
    end_time        = Column(DateTime(timezone=True))
    recurrence_rule = Column(String(500), nullable=True)

    # Visibility
    visibility  = Column(Enum(EventVisibility), default=EventVisibility.PUBLIC_GROUP, nullable=False)

    created_at  = Column(DateTime(timezone=True), default=utcnow)
    updated_at  = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    is_cancelled = Column(Boolean, default=False)

    # Relationships
    creator     = relationship("Student", back_populates="created_events", foreign_keys=[creator_id])
    group       = relationship("Group", back_populates="events")
    location    = relationship("CampusLocation", back_populates="events")
    invitations = relationship("EventInvitation", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event '{self.title}' in {self.group}>"


class EventInvitation(Base):
    """
    Tracks who has been invited to a specific event.

    For PUBLIC_GROUP events: a row is auto-created for every group member (status=PENDING).
    For INVITED_ONLY events: rows are only created for explicitly invited students.

    The map pin query checks for non-declined invitations to determine visibility.
    invited_by is null for system-generated invitations (public group events).
    """
    __tablename__ = "event_invitations"

    id           = Column(Integer, primary_key=True, index=True)
    event_id     = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    student_id   = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    invited_by   = Column(Integer, ForeignKey("students.id"))  # null = system-generated
    status       = Column(Enum(InviteStatus), default=InviteStatus.PENDING, nullable=False)
    invited_at   = Column(DateTime(timezone=True), default=utcnow)
    responded_at = Column(DateTime(timezone=True))

    # Relationships
    event   = relationship("Event", back_populates="invitations")
    student = relationship("Student", back_populates="invitations", foreign_keys=[student_id])
    inviter = relationship("Student", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<Invitation event={self.event_id} student={self.student_id} status={self.status}>"


class Message(Base):
    """
    A message posted in a group's message board.

    message_type=SYSTEM rows are auto-created by the backend when
    students join or leave a group. They appear as greyed-out notices
    in the chat feed and have no author (author_id=None).
    """
    __tablename__ = "messages"

    id           = Column(Integer, primary_key=True, index=True)
    group_id     = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    author_id    = Column(Integer, ForeignKey("students.id"), nullable=True)  # null for system messages
    content      = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.USER, nullable=False)
    created_at   = Column(DateTime(timezone=True), default=utcnow, index=True)
    is_deleted   = Column(Boolean, default=False)  # soft delete — never hard-delete messages

    # Relationships
    group  = relationship("Group",   backref="messages")
    author = relationship("Student", backref="messages", foreign_keys=[author_id])

    def __repr__(self):
        return f"<Message group={self.group_id} type={self.message_type.value}>"


class OTPRequest(Base):
    """
    Stores one-time password codes for email verification and password reset.

    The OTP itself is stored as a bcrypt hash — never plaintext.
    expires_at is set to created_at + 10 minutes by the auth route.
    used is set to True the moment the OTP is verified so it cannot be reused.
    """
    __tablename__ = "otp_requests"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(255), nullable=False, index=True)
    otp_hash   = Column(String(255), nullable=False)  # bcrypt hash of the 6-digit code
    created_at = Column(DateTime(timezone=True), default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # created_at + 10 minutes
    used       = Column(Boolean, default=False)   # True once verified — prevents reuse

    def __repr__(self):
        return f"<OTPRequest email={self.email} used={self.used}>"
