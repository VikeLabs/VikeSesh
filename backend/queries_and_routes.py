"""
UVic Campus Events - Key Queries & FastAPI Route Examples
These show how the Next.js frontend would call your Python backend.
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
from models import Student, Group, Event, EventInvitation, EventVisibility, InviteStatus

# 
# DB SETUP
# ─────────────────────────────────────────────

DATABASE_URL = "postgresql://user:password@localhost/uvic_events"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────
# KEY QUERIES (the heart of your app)
# ─────────────────────────────────────────────

def get_map_pins_for_student(student_id: int, db: Session):
    """
    THE CORE QUERY: Returns all events that should appear as
    map pins for a given student.

    Rules:
      1. Student must be a member of the event's group.
      2. Either the event is PUBLIC_GROUP -> visible to all group members
         OR the student has an invitation -> INVITED_ONLY events
    """
    student = db.get(Student, student_id)
    group_ids = [g.id for g in student.groups]

    # Get public events in the student's groups
    public_events = (
        db.query(Event)
        .filter(
            Event.group_id.in_(group_ids),
            Event.visibility == EventVisibility.PUBLIC_GROUP,
            Event.is_cancelled == False,
        )
        .all()
    )

    # Get private events where the student was explicitly invited
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
    invited_student_ids: list[int],   # only used for INVITED_ONLY
    db: Session,
):
    """
    Creates an event and sets up invitations.
    - PUBLIC_GROUP  → auto-invite all group members
    - INVITED_ONLY  → invite only the specified student IDs
    """
    event = Event(**event_data, creator_id=creator_id, group_id=group_id)
    db.add(event)
    db.flush()  # get event.id before commit

    if event.visibility == EventVisibility.PUBLIC_GROUP:
        # Find all members of the group and create invitations for them
        group = db.get(Group, group_id)
        for member in group.members:
            invitation = EventInvitation(
                event_id=event.id,
                student_id=member.id,
                invited_by=None,  # system-generated
            )
            db.add(invitation)
    else:
        # Only invite explicitly listed students
        for sid in invited_student_ids:
            invitation = EventInvitation(
                event_id=event.id,
                student_id=sid,
                invited_by=creator_id,
            )
            db.add(invitation)

    db.commit()
    return event


# ─────────────────────────────────────────────
# FASTAPI ROUTES (called by Next.js frontend)
# ─────────────────────────────────────────────

@app.get("/api/map-pins/{student_id}")
def map_pins(student_id: int, db: Session = Depends(get_db)):
    """
    Next.js calls this to get all map pin data for the campus map.
    Returns event locations + metadata for the logged-in student.
    """
    events = get_map_pins_for_student(student_id, db)
    return [
        {
            "event_id":    e.id,
            "title":       e.title,
            "start_time":  e.start_time.isoformat(),
            "latitude":    e.location.latitude  if e.location else None,
            "longitude":   e.location.longitude if e.location else None,
            "location_name": e.location.name   if e.location else None,
            "group_name":  e.group.name,
            "visibility":  e.visibility.value,
        }
        for e in events if e.location  # only pin events that have a campus location
    ]


@app.post("/api/groups/{group_id}/join")
def join_group(group_id: int, student_id: int, db: Session = Depends(get_db)):
    """Student joins a group (e.g. enrolls in MATH 100 group)."""
    group = db.get(Group, group_id)
    student = db.get(Student, student_id)
    if not group or not student:
        raise HTTPException(status_code=404)
    if student not in group.members:
        group.members.append(student)
        db.commit()
    return {"status": "joined", "group": group.name}


@app.get("/api/students/{student_id}/groups")
def list_groups(student_id: int, db: Session = Depends(get_db)):
    """Returns all groups a student belongs to."""
    student = db.get(Student, student_id)
    return [{"id": g.id, "name": g.name, "course_code": g.course_code} for g in student.groups]


@app.post("/api/events/{event_id}/respond")
def respond_to_invite(event_id: int, student_id: int, accepted: bool, db: Session = Depends(get_db)):
    """Student accepts or declines an event invitation."""
    from datetime import datetime
    invite = (
        db.query(EventInvitation)
        .filter_by(event_id=event_id, student_id=student_id)
        .first()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    invite.status = InviteStatus.ACCEPTED if accepted else InviteStatus.DECLINED
    invite.responded_at = datetime.utcnow()
    db.commit()
    return {"status": invite.status.value}
