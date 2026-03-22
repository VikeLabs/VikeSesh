"""
VikeSesh — Group Routes
"""

from flask import Blueprint, request
from backend.extensions import db
from backend.models import Group, Student, Message, MessageType
from backend.queries import is_group_member
from backend.lib.responses import success, error

groups_bp = Blueprint("groups", __name__)


@groups_bp.get("/groups")
def list_groups():
    """
    GET /api/groups
    GET /api/groups?search=math
    GET /api/groups?page=2
    """
    search = request.args.get("search", "").strip()
    page   = int(request.args.get("page", 1))
    limit  = 20
    offset = (page - 1) * limit

    query = Group.query.filter(Group.is_public == True)

    if search:
        query = query.filter(
            Group.name.ilike(f"%{search}%") |
            Group.course_code.ilike(f"%{search}%")
        )

    total  = query.count()
    groups = query.offset(offset).limit(limit).all()

    return success({
        "groups": [
            {
                "id":              g.id,
                "name":            g.name,
                "description":     g.description,
                "course_code":     g.course_code,
                "icon_url":        g.icon_url,
                "member_count":    len(g.members),
                "parent_group_id": g.parent_group_id,
            }
            for g in groups
        ],
        "page":  page,
        "total": total,
    })


@groups_bp.get("/groups/<int:group_id>")
def get_group(group_id):
    """
    GET /api/groups/<group_id>?student_id=<student_id>
    """
    group = db.session.get(Group, group_id)
    if not group:
        return error("Group not found", 404)

    # TODO: replace student_id query param with JWT auth (Role 2)
    student_id = request.args.get("student_id", type=int)
    if not group.is_public:
        if not student_id or not is_group_member(student_id, group_id):
            return error("You are not a member of this group", 403)

    return success({
        "id":              group.id,
        "name":            group.name,
        "description":     group.description,
        "course_code":     group.course_code,
        "icon_url":        group.icon_url,
        "is_public":       group.is_public,
        "member_count":    len(group.members),
        "parent_group_id": group.parent_group_id,
        "subgroups": [
            {"id": s.id, "name": s.name}
            for s in group.subgroups
        ],
        "members": [
            {
                "id":           m.id,
                "display_name": m.display_name,
                "avatar_url":   m.avatar_url,
            }
            for m in group.members
        ],
    })


@groups_bp.post("/groups")
def create_group():
    """
    POST /api/groups
    Body: { "name": "MATH 100", "description": "...", "course_code": "MATH100",
            "is_public": true, "student_id": 1, "parent_group_id": null }
    """
    body = request.get_json()
    if not body:
        return error("Request body is required")

    name       = body.get("name", "").strip()
    student_id = body.get("student_id")

    # TODO: replace student_id body param with JWT auth (Role 2)
    if not name:
        return error("Group name is required")
    if not student_id:
        return error("student_id is required")

    student = db.session.get(Student, student_id)
    if not student:
        return error("Student not found", 404)

    group = Group(
        name            = name,
        description     = body.get("description"),
        course_code     = body.get("course_code"),
        is_public       = body.get("is_public", True),
        created_by      = student_id,
        parent_group_id = body.get("parent_group_id"),
    )
    db.session.add(group)
    db.session.flush()
    group.members.append(student)
    db.session.commit()

    return success({"id": group.id, "name": group.name}, 201)


@groups_bp.post("/groups/<int:group_id>/join")
def join_group(group_id):
    """
    POST /api/groups/<group_id>/join
    Body: { "student_id": 1 }
    """
    body       = request.get_json() or {}
    student_id = body.get("student_id")

    # TODO: replace student_id body param with JWT auth (Role 2)
    if not student_id:
        return error("student_id is required")

    group   = db.session.get(Group, group_id)
    student = db.session.get(Student, student_id)

    if not group:
        return error("Group not found", 404)
    if not student:
        return error("Student not found", 404)
    if student in group.members:
        return error("Already a member of this group", 409)

    group.members.append(student)

    # Auto-post system message to group chat
    db.session.add(Message(
        group_id     = group_id,
        author_id    = None,
        content      = f"{student.display_name} joined the group.",
        message_type = MessageType.SYSTEM,
    ))

    db.session.commit()
    return success({"status": "joined", "group": group.name}, 201)


@groups_bp.delete("/groups/<int:group_id>/leave")
def leave_group(group_id):
    """
    DELETE /api/groups/<group_id>/leave
    Body: { "student_id": 1 }
    """
    body       = request.get_json() or {}
    student_id = body.get("student_id")

    # TODO: replace student_id body param with JWT auth (Role 2)
    if not student_id:
        return error("student_id is required")

    group   = db.session.get(Group, group_id)
    student = db.session.get(Student, student_id)

    if not group:
        return error("Group not found", 404)
    if student not in group.members:
        return error("You are not a member of this group", 403)

    if group.created_by == student_id and len(group.members) > 1:
        return error(
            "You are the group owner. Transfer ownership before leaving.",
            403
        )

    group.members.remove(student)

    db.session.add(Message(
        group_id     = group_id,
        author_id    = None,
        content      = f"{student.display_name} left the group.",
        message_type = MessageType.SYSTEM,
    ))

    db.session.commit()
    return success({"status": "left", "group": group.name})
