
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean,
    DateTime, Float, ForeignKey, Enum, Table
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

#
# ENUMS
#

class EventVisibility(enum.Enum):
    PUBLIC_GROUP = "public_group"   # Visible to all group members
    INVITED_ONLY = "invited_only"   # Only explicitly invited members


class InviteStatus(enum.Enum):
    PENDING  = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class MemberRole(enum.Enum):
    OWNER   = "owner"    # Created the group, full control // **MIGHT REMOVE LATER**
    ADMIN = "admin"  # Can edit group and manage members
    MEMBER  = "member"   # Standard member


#
# ASSOCIATION TABLES (Many-to-Many)
# 

# Which students are in which groups
group_memberships = Table(
    "group_memberships",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id"), primary_key=True),
    Column("group_id",   Integer, ForeignKey("groups.id"),   primary_key=True),
    Column("role",       Enum(MemberRole), default=MemberRole.MEMBER),
    Column("joined_at",  DateTime, default=datetime.utcnow),
)


# 
# CORE MODELS
# 

class Student(Base):
    """A UVic student account."""
    __tablename__ = "students"

    id             = Column(Integer, primary_key=True, index=True)
    uvic_email     = Column(String(255), unique=True, nullable=False, index=True)
    display_name   = Column(String(100), nullable=False)
    student_number = Column(String(20), unique=True)
    avatar_url     = Column(String(500))
    created_at     = Column(DateTime, default=datetime.utcnow)
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
    """
    __tablename__ = "groups"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150), nullable=False)          # e.g. "MATH 100"
    description = Column(Text)
    course_code = Column(String(20), index=True)               # e.g. "MATH100"  null for clubs
    icon_url    = Column(String(500))
    is_public   = Column(Boolean, default=True)                # Can anyone join?
    created_at  = Column(DateTime, default=datetime.utcnow)
    created_by  = Column(Integer, ForeignKey("students.id"))

    parent_group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    parent_group    = relationship("Group", remote_side=lambda: [Group.id], back_populates="subgroups")
    subgroups       = relationship("Group", back_populates="parent_group")
    # Relationships
    members     = relationship("Student", secondary=group_memberships, back_populates="groups")
    events      = relationship("Event", back_populates="group")

    def __repr__(self):
        return f"<Group {self.name}>"


class CampusLocation(Base):
    """
    A named spot on campus (building, courtyard, etc.).
    These appear as map pins in the Next.js frontend.
    """
    __tablename__ = "campus_locations"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)          # e.g. "Clearihue A110"
    building    = Column(String(100))                          # e.g. "Clearihue"
    room        = Column(String(50))                           # e.g. "A110"
    latitude    = Column(Float, nullable=False)                # For map pin placement
    longitude   = Column(Float, nullable=False)

    # Relationships
    events      = relationship("Event", back_populates="location")

    def __repr__(self):
        return f"<CampusLocation {self.name}>"


class Event(Base):
    """
    An event created within a group.
    Visibility controls whether all group members see it or only invited ones.
    """
    __tablename__ = "events"

    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(200), nullable=False)
    description  = Column(Text)
    creator_id   = Column(Integer, ForeignKey("students.id"), nullable=False)
    group_id     = Column(Integer, ForeignKey("groups.id"), nullable=False)
    location_id  = Column(Integer, ForeignKey("campus_locations.id"))

    # Scheduling
    start_time      = Column(DateTime, nullable=False)
    end_time        = Column(DateTime)
    # RFC 5545 RRULE string for recurring events, e.g. "FREQ=WEEKLY;BYDAY=MO,WE;UNTIL=20260601T000000Z"
    # Null means the event is a one-time occurrence.
    recurrence_rule = Column(String(500), nullable=True)

    # Visibility: PUBLIC_GROUP = map pin shown to all members; INVITED_ONLY = only invitees
    visibility   = Column(Enum(EventVisibility), default=EventVisibility.PUBLIC_GROUP, nullable=False)

    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_cancelled = Column(Boolean, default=False)

    # Relationships
    creator      = relationship("Student", back_populates="created_events", foreign_keys=[creator_id])
    group        = relationship("Group", back_populates="events")
    location     = relationship("CampusLocation", back_populates="events")
    invitations  = relationship("EventInvitation", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event '{self.title}' in {self.group}>"


class EventInvitation(Base):
    """
    Tracks who has been invited to a specific event.

    For PUBLIC_GROUP events:  a row is auto-created for every group member (status=PENDING).
    For INVITED_ONLY events:  rows are only created for explicitly invited students.

    The map pin query simply checks for accepted/pending invitations.
    """
    __tablename__ = "event_invitations"

    id          = Column(Integer, primary_key=True, index=True)
    event_id    = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    student_id  = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    invited_by  = Column(Integer, ForeignKey("students.id"))   # null = system (public event)
    status      = Column(Enum(InviteStatus), default=InviteStatus.PENDING, nullable=False)
    invited_at  = Column(DateTime, default=datetime.utcnow)
    responded_at= Column(DateTime)

    # Relationships
    event       = relationship("Event", back_populates="invitations")
    student     = relationship("Student", back_populates="invitations", foreign_keys=[student_id])
    inviter     = relationship("Student", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<Invitation event={self.event_id} student={self.student_id} status={self.status}>"


class MessageType(enum.Enum):
    USER   = "user"    # Posted by a student
    SYSTEM = "system"  # Auto-generated (e.g. "[Alice] joined the group")


class Message(Base):
    """
    A message posted in a group's message board.

    message_type=SYSTEM rows are auto-created by the backend when
    students join or leave a group — they appear as greyed-out
    notices in the chat feed.

    author_id is nullable so that SYSTEM messages don't need a real author.
    """
    __tablename__ = "messages"

    id           = Column(Integer, primary_key=True, index=True)
    group_id     = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    author_id    = Column(Integer, ForeignKey("students.id"), nullable=True)  # null for system messages
    content      = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.USER, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, index=True)
    is_deleted   = Column(Boolean, default=False)  # soft delete — never hard-delete messages

    # Relationships
    group        = relationship("Group",   backref="messages")
    author       = relationship("Student", backref="messages", foreign_keys=[author_id])

    def __repr__(self):
        return f"<Message group={self.group_id} type={self.message_type.value}>"
