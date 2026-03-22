"""
VikeSesh — Event Routes
"""

from datetime import datetime, timezone
from flask import Blueprint, request
from backend.extensions import db
from backend.models import Event, EventInvitation, EventVisibility, InviteStatus
from backend.queries import create_event_and_notify, is_group_member
from backend.lib.responses import success, error

events_bp = Blueprint("events", __name__)


@events_bp.get("/groups/<int:group_id>/events")
def list_events(group_id):
    """
    GET /api/groups/<group_id>/events?student_id=<id>
    """
    student_id = request.args.get("student_id", type=int)

    # TODO: replace student_id query param with JWT auth (Role 2)
    if not student_id:
        return error("student_id is required")
    if not is_group_member(student_id, group_id):
        return error("You are not a member of this group", 403)

    events = Event.query.filter(
        Event.group_id    == group_id,
        Event.is_cancelled == False,
    ).order_by(Event.start_time).all()

    return success([
        {
            "id":              e.id,
            "title":           e.title,
            "description":     e.description,
            "start_time":      e.start_time.isoformat() if e.start_time else None,
            "end_time":        e.end_time.isoformat() if e.end_time else None,
            "recurrence_rule": e.recurrence_rule,
            "visibility":      e.visibility.value,
            "is_cancelled":    e.is_cancelled,
            "creator_id":      e.creator_id,
            "location": {
                "id":        e.location.id,
                "name":      e.location.name,
                "building":  e.location.building,
                "room":      e.location.room,
                "latitude":  e.location.latitude,
                "longitude": e.location.longitude,
            } if e.location else None,
        }
        for e in events
    ])


@events_bp.post("/groups/<int:group_id>/events")
def create_event(group_id):
    """
    POST /api/groups/<group_id>/events
    Body: { "student_id": 1, "title": "...", "start_time": "...",
            "visibility": "public_group", "location_id": 1,
            "invited_student_ids": [] }
    """
    body       = request.get_json() or {}
    student_id = body.get("student_id")

    # TODO: replace student_id body param with JWT auth (Role 2)
    if not student_id:
        return error("student_id is required")
    if not is_group_member(student_id, group_id):
        return error("You are not a member of this group", 403)

    title      = body.get("title", "").strip()
    start_time = body.get("start_time")
    visibility = body.get("visibility", "public_group")

    if not title:
        return error("Event title is required")
    if not start_time:
        return error("start_time is required")

    try:
        vis = EventVisibility(visibility)
    except ValueError:
        return error("visibility must be 'public_group' or 'invited_only'")

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt   = datetime.fromisoformat(body["end_time"].replace("Z", "+00:00")) if body.get("end_time") else None
    except (ValueError, KeyError):
        return error("Invalid datetime format. Use ISO 8601 e.g. 2026-03-01T14:00:00Z")

    event_data = {
        "title":           title,
        "description":     body.get("description"),
        "location_id":     body.get("location_id"),
        "start_time":      start_dt,
        "end_time":        end_dt,
        "visibility":      vis,
        "recurrence_rule": body.get("recurrence_rule"),
    }

    invited_ids = body.get("invited_student_ids", [])
    event = create_event_and_notify(student_id, group_id, event_data, invited_ids)
    db.session.commit()

    return success({"id": event.id, "title": event.title}, 201)


@events_bp.post("/events/<int:event_id>/respond")
def respond_to_invite(event_id):
    """
    POST /api/events/<event_id>/respond
    Body: { "student_id": 1, "accepted": true }
    """
    body       = request.get_json() or {}
    student_id = body.get("student_id")
    accepted   = body.get("accepted")

    # TODO: replace student_id body param with JWT auth (Role 2)
    if student_id is None:
        return error("student_id is required")
    if accepted is None:
        return error("accepted (true or false) is required")

    invite = EventInvitation.query.filter_by(
        event_id=event_id, student_id=student_id
    ).first()

    if not invite:
        return error("Invitation not found", 404)

    invite.status       = InviteStatus.ACCEPTED if accepted else InviteStatus.DECLINED
    invite.responded_at = datetime.now(timezone.utc)
    db.session.commit()

    return success({"status": invite.status.value})


@events_bp.patch("/events/<int:event_id>")
def update_event(event_id):
    """
    PATCH /api/events/<event_id>
    Body: { "student_id": 1, "title": "New Title", ... }
    """
    body       = request.get_json() or {}
    student_id = body.get("student_id")

    # TODO: replace student_id body param with JWT auth (Role 2)
    if not student_id:
        return error("student_id is required")

    event = db.session.get(Event, event_id)
    if not event:
        return error("Event not found", 404)
    if event.creator_id != student_id:
        return error("Only the event creator can edit this event", 403)

    if "title" in body and body["title"].strip():
        event.title = body["title"].strip()
    if "description" in body:
        event.description = body["description"]
    if "location_id" in body:
        event.location_id = body["location_id"]
    if "recurrence_rule" in body:
        event.recurrence_rule = body["recurrence_rule"]

    db.session.commit()
    return success({"id": event.id, "title": event.title})


@events_bp.delete("/events/<int:event_id>")
def cancel_event(event_id):
    """
    DELETE /api/events/<event_id>
    Body: { "student_id": 1 }
    """
    body       = request.get_json() or {}
    student_id = body.get("student_id")

    # TODO: replace student_id body param with JWT auth (Role 2)
    if not student_id:
        return error("student_id is required")

    event = db.session.get(Event, event_id)
    if not event:
        return error("Event not found", 404)
    if event.creator_id != student_id:
        return error("Only the event creator can cancel this event", 403)

    event.is_cancelled = True
    db.session.commit()

    return success({"status": "cancelled", "event_id": event_id})
