"""
VikeSesh — Core Query Functions
These are the most important database queries in the app.
They live here (separate from routes) so any blueprint can import
them without circular imports.

With Flask-SQLAlchemy, queries use Model.query instead of db.session.query.
All functions that need a db session use db from extensions.py.
"""

from backend.extensions import db
from backend.models import (
    Student, Group, Event, EventInvitation,
    EventVisibility, InviteStatus
)


def get_map_pins_for_student(student_id: int):
    """
    THE CORE QUERY — Returns all events that should appear as
    map pins for a given student.

    Rules:
      1. Student must be a member of the event's group.
      2. Either the event is PUBLIC_GROUP (visible to all group members)
         OR the student has a non-declined invitation (INVITED_ONLY events).
      3. Cancelled events are never returned.
    """
    student = db.session.get(Student, student_id)
    if not student:
        return []

    group_ids = [g.id for g in student.groups]
    if not group_ids:
        return []

    # Public events in any group the student belongs to
    public_events = Event.query.filter(
        Event.group_id.in_(group_ids),
        Event.visibility == EventVisibility.PUBLIC_GROUP,
        Event.is_cancelled == False,
    ).all()

    # Invite-only events where the student has a non-declined invitation
    invited_events = Event.query.join(
        EventInvitation, Event.id == EventInvitation.event_id
    ).filter(
        EventInvitation.student_id == student_id,
        EventInvitation.status != InviteStatus.DECLINED,
        Event.visibility == EventVisibility.INVITED_ONLY,
        Event.is_cancelled == False,
    ).all()

    return public_events + invited_events


def create_event_and_notify(creator_id: int, group_id: int, event_data: dict, invited_student_ids: list):
    """
    Creates an event and sets up the correct invitations.

    PUBLIC_GROUP  → auto-creates an EventInvitation for every group member.
    INVITED_ONLY  → only creates invitations for the listed student IDs.

    Does NOT call db.session.commit() — the caller is responsible.
    Returns the created Event object.
    """
    event = Event(**event_data, creator_id=creator_id, group_id=group_id)
    db.session.add(event)
    db.session.flush()  # gets event.id without committing

    if event.visibility == EventVisibility.PUBLIC_GROUP:
        group = db.session.get(Group, group_id)
        for member in group.members:
            db.session.add(EventInvitation(
                event_id=event.id,
                student_id=member.id,
                invited_by=None,  # null = system-generated
            ))
    else:
        for sid in invited_student_ids:
            db.session.add(EventInvitation(
                event_id=event.id,
                student_id=sid,
                invited_by=creator_id,
            ))

    return event


def is_group_member(student_id: int, group_id: int) -> bool:
    """
    Returns True if the student is a member of the group.
    Used by routes to check access before doing anything.
    """
    student = db.session.get(Student, student_id)
    if not student:
        return False
    return any(g.id == group_id for g in student.groups)
