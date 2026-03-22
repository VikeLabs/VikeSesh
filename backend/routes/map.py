"""
VikeSesh — Map Routes
"""

from flask import Blueprint
from backend.queries import get_map_pins_for_student
from backend.lib.responses import success, error

map_bp = Blueprint("map", __name__)


@map_bp.get("/map-pins/<int:student_id>")
def map_pins(student_id):
    """
    GET /api/map-pins/<student_id>

    Returns all event map pins visible to the student.
    Called by Next.js on campus map page load.
    Only events with a campus location are included.
    """
    # TODO: replace student_id path param with JWT auth (Role 2)
    events = get_map_pins_for_student(student_id)

    pins = [
        {
            "event_id":      e.id,
            "title":         e.title,
            "start_time":    e.start_time.isoformat() if e.start_time else None,
            "end_time":      e.end_time.isoformat() if e.end_time else None,
            "latitude":      e.location.latitude,
            "longitude":     e.location.longitude,
            "location_name": e.location.name,
            "group_name":    e.group.name,
            "group_id":      e.group.id,
            "visibility":    e.visibility.value,
        }
        for e in events
        if e.location
    ]

    return success(pins)
