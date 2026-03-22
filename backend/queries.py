"""
VikeSesh — Core Query Functions
These are the most important database queries in the app.
They live here (separate from routes) so any blueprint can import
them without circular imports.

All functions take a SQLAlchemy session (db) as their last argument.
Get a session by calling get_db() from database.py.
"""

from models import (
    Student, Group, Event, EventInvitation,
    EventVisibility, InviteStatus
)


def get_map_pins_for_student(student_id: int, db):
    """
    THE CORE QUERY — Returns all events that should appear as
    map pins for a given student.

    Rules:
      1. Student must be a member of the event's group.
      2. Either the event is PUBLIC_GROUP (visible to all group members)
         OR the student has a non-declined invitation (INVITED_ONLY events).
      3. Cancelled events are never returned.

    This is called by the /api/map-pins/<student_id> route and
    drives the entire campus map feature.
    """
    student = db.get(Student, student_id)

    # If student doesn't exist or has no groups, return empty list
    if not student:
        return []

    group_ids = [g.id for g in student.groups]

    if not group_ids:
        return []

    # Public events in any group the student belongs to
    public_events = (
        db.query(Event)
        .filter(
            Event.group_id.in_(group_ids),
            Event.visibility == EventVisibility.PUBLIC_GROUP,
            Event.is_cancelled == False,
        )
        .all()
    )

    # Invite-only events where the student has a non-declined invitation
    invited_events = (
        db.query(Event)
        .join(EventInvitation, Event.id == EventInvitation.event_id)
        .filter(
            EventInvitation.student_id == student_id,
            EventInvitation.status != InviteStatus.DECLINED,
            Event.visibility == EventVisibility.INVITED_ONLY,
            Event.is_cancelled == False,
        )
        .all()
    )

    return public_events + invited_events


def create_event_and_notify(
    creator_id: int,
    group_id: int,
    event_data: dict,
    invited_student_ids: list,
    db,
):
    """
    Creates an event and sets up the correct invitations.

    PUBLIC_GROUP  → auto-creates an EventInvitation for every group member
                    so they all see the map pin immediately.
    INVITED_ONLY  → only creates invitations for the explicitly listed student IDs.

    invited_student_ids is ignored for PUBLIC_GROUP events.

    Returns the created Event object.
    Does NOT call db.commit() — the caller is responsible for committing.
    """
    event = Event(**event_data, creator_id=creator_id, group_id=group_id)
    db.add(event)
    db.flush()  # Assigns event.id without committing the transaction

    if event.visibility == EventVisibility.PUBLIC_GROUP:
        group = db.get(Group, group_id)
        for member in group.members:
            invitation = EventInvitation(
                event_id=event.id,
                student_id=member.id,
                invited_by=None,  # None = system-generated, not a manual invite
            )
            db.add(invitation)
    else:
        for sid in invited_student_ids:
            invitation = EventInvitation(
                event_id=event.id,
                student_id=sid,
                invited_by=creator_id,
            )
            db.add(invitation)

    return event


def get_group_members(group_id: int, db):
    """
    Returns all Student objects who are members of a given group.
    Used by routes that need to display member lists.
    """
    group = db.get(Group, group_id)
    if not group:
        return []
    return group.members


def is_group_member(student_id: int, group_id: int, db) -> bool:
    """
    Returns True if the student is a member of the group, False otherwise.
    Used by decorators and routes to check access before doing anything.
    """
    student = db.get(Student, student_id)
    if not student:
        return False
    return any(g.id == group_id for g in student.groups)
