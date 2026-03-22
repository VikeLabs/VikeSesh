"""
VikeSesh — Message Routes
"""

from flask import Blueprint, request
from backend.extensions import db
from backend.models import Message, MessageType
from backend.queries import is_group_member
from backend.lib.responses import success, error

messages_bp = Blueprint("messages", __name__)

MAX_MESSAGE_LENGTH = 2000


@messages_bp.get("/groups/<int:group_id>/messages")
def list_messages(group_id):
    """
    GET /api/groups/<group_id>/messages?student_id=<id>
    GET /api/groups/<group_id>/messages?student_id=<id>&before=<message_id>
    """
    student_id = request.args.get("student_id", type=int)
    before_id  = request.args.get("before", type=int)
    limit      = 50

    # TODO: replace student_id query param with JWT auth (Role 2)
    if not student_id:
        return error("student_id is required")
    if not is_group_member(student_id, group_id):
        return error("You are not a member of this group", 403)

    query = Message.query.filter(
        Message.group_id   == group_id,
        Message.is_deleted == False,
    )

    if before_id:
        query = query.filter(Message.id < before_id)

    messages = query.order_by(Message.id.desc()).limit(limit + 1).all()
    has_more = len(messages) > limit
    messages = messages[:limit]

    return success({
        "messages": [
            {
                "id":           m.id,
                "content":      m.content,
                "message_type": m.message_type.value,
                "created_at":   m.created_at.isoformat() if m.created_at else None,
                "author": {
                    "id":           m.author.id,
                    "display_name": m.author.display_name,
                    "avatar_url":   m.author.avatar_url,
                } if m.author else None,
            }
            for m in messages
        ],
        "has_more": has_more,
    })


@messages_bp.post("/groups/<int:group_id>/messages")
def post_message(group_id):
    """
    POST /api/groups/<group_id>/messages
    Body: { "student_id": 1, "content": "Hey everyone!" }
    """
    body       = request.get_json() or {}
    student_id = body.get("student_id")
    content    = body.get("content", "").strip()

    # TODO: replace student_id body param with JWT auth (Role 2)
    if not student_id:
        return error("student_id is required")
    if not content:
        return error("Message content cannot be empty")
    if len(content) > MAX_MESSAGE_LENGTH:
        return error(f"Message cannot exceed {MAX_MESSAGE_LENGTH} characters")
    if not is_group_member(student_id, group_id):
        return error("You are not a member of this group", 403)

    msg = Message(
        group_id     = group_id,
        author_id    = student_id,
        content      = content,
        message_type = MessageType.USER,
    )
    db.session.add(msg)
    db.session.commit()

    return success({"id": msg.id, "content": msg.content}, 201)
