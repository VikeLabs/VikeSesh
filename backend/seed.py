"""
VikeSesh — Seed Script
Populates the database with realistic test data.

Usage (from repo root):
    python -m backend.seed

WARNING: Drops and recreates all tables. Never run against production.
"""

from datetime import datetime, timedelta, timezone
from backend.app import app
from backend.extensions import db
from backend.models import (
    Student, Group, CampusLocation, Event, EventInvitation,
    Message, EventVisibility, InviteStatus, MessageType
)


def seed():
    now = datetime.now(timezone.utc)

    # ── Students ─────────────────────────────────────────────
    alice = Student(email="alice@uvic.ca",  password_hash="hashed", display_name="Alice Chen",   student_number="V00111111", is_verified=True)
    bob   = Student(email="bob@uvic.ca",    password_hash="hashed", display_name="Bob Martins",  student_number="V00222222", is_verified=True)
    carol = Student(email="carol@uvic.ca",  password_hash="hashed", display_name="Carol Singh",  student_number="V00333333", is_verified=True)
    dan   = Student(email="dan@uvic.ca",    password_hash="hashed", display_name="Dan Kowalski", student_number="V00444444", is_verified=True)
    eve   = Student(email="eve@uvic.ca",    password_hash="hashed", display_name="Eve Thompson", student_number="V00555555", is_verified=True)

    db.session.add_all([alice, bob, carol, dan, eve])
    db.session.flush()

    # ── Campus Locations ─────────────────────────────────────
    clearihue = CampusLocation(name="Clearihue A110",         building="Clearihue",        room="A110", latitude=48.4636, longitude=-123.3117)
    elliot    = CampusLocation(name="Elliott 168",             building="Elliott",          room="168",  latitude=48.4629, longitude=-123.3104)
    library   = CampusLocation(name="McPherson Library",       building="McPherson Library",room=None,   latitude=48.4634, longitude=-123.3096)
    ssc       = CampusLocation(name="Student Union Building",  building="SUB",              room=None,   latitude=48.4641, longitude=-123.3131)
    cornett   = CampusLocation(name="Cornett A128",            building="Cornett",          room="A128", latitude=48.4625, longitude=-123.3109)
    petch     = CampusLocation(name="Petch Fountain",          building="Outdoor",          room=None,   latitude=48.4638, longitude=-123.3122)

    db.session.add_all([clearihue, elliot, library, ssc, cornett, petch])
    db.session.flush()

    # ── Groups ───────────────────────────────────────────────
    math100       = Group(name="MATH 100",             course_code="MATH100", description="Calculus 1 — all sections",            is_public=True,  created_by=alice.id)
    math100_smith = Group(name="MATH 100 — Dr. Smith", course_code="MATH100", description="Dr. Smith's Tuesday/Thursday section", is_public=True,  created_by=alice.id)
    chess_club    = Group(name="Chess Club",            course_code=None,      description="Weekly chess meetups on campus",       is_public=True,  created_by=bob.id)
    bar_crawl     = Group(name="Bar Crawl Nights 2025", course_code=None,      description="Monthly bar crawl crew",              is_public=False, created_by=carol.id)

    db.session.add_all([math100, chess_club, bar_crawl, math100_smith])
    db.session.flush()

    math100_smith.parent_group_id = math100.id

    # ── Memberships ──────────────────────────────────────────
    math100.members.extend([alice, bob, carol])
    math100_smith.members.extend([alice, bob])
    chess_club.members.extend([bob, dan, eve])
    bar_crawl.members.extend([carol, dan, eve])
    db.session.flush()

    # ── Events ───────────────────────────────────────────────
    midterm_review = Event(
        title="MATH 100 Midterm Review",
        description="Group study session before the midterm. Bring practice problems.",
        creator_id=alice.id, group_id=math100.id, location_id=clearihue.id,
        start_time=now + timedelta(days=2, hours=14),
        end_time=now + timedelta(days=2, hours=16),
        visibility=EventVisibility.PUBLIC_GROUP,
    )
    weekly_study = Event(
        title="Weekly MATH 100 Study Group",
        description="Every Tuesday at the library. All welcome.",
        creator_id=bob.id, group_id=math100.id, location_id=library.id,
        start_time=now + timedelta(days=1, hours=13),
        end_time=now + timedelta(days=1, hours=15),
        visibility=EventVisibility.PUBLIC_GROUP,
        recurrence_rule="FREQ=WEEKLY;BYDAY=TU;COUNT=10",
    )
    bar_crawl_event = Event(
        title="October Bar Crawl",
        description="Starting at the Grad House, ending wherever.",
        creator_id=carol.id, group_id=bar_crawl.id, location_id=ssc.id,
        start_time=now + timedelta(days=5, hours=21),
        end_time=now + timedelta(days=5, hours=23, minutes=59),
        visibility=EventVisibility.INVITED_ONLY,
    )
    chess_tournament = Event(
        title="Chess Club Tournament",
        description="Single elimination. Bring your own clock if you have one.",
        creator_id=dan.id, group_id=chess_club.id, location_id=cornett.id,
        start_time=now + timedelta(days=3, hours=10),
        end_time=now + timedelta(days=3, hours=13),
        visibility=EventVisibility.PUBLIC_GROUP,
    )
    cancelled_event = Event(
        title="Cancelled Study Session",
        description="This was cancelled.",
        creator_id=alice.id, group_id=math100.id, location_id=elliot.id,
        start_time=now + timedelta(days=1),
        visibility=EventVisibility.PUBLIC_GROUP,
        is_cancelled=True,
    )

    db.session.add_all([midterm_review, weekly_study, bar_crawl_event, chess_tournament, cancelled_event])
    db.session.flush()

    # ── Invitations ──────────────────────────────────────────
    for event, group in [(midterm_review, math100), (weekly_study, math100), (chess_tournament, chess_club)]:
        for member in group.members:
            db.session.add(EventInvitation(event_id=event.id, student_id=member.id, invited_by=None, status=InviteStatus.PENDING))

    for student in [carol, dan]:
        db.session.add(EventInvitation(event_id=bar_crawl_event.id, student_id=student.id, invited_by=carol.id, status=InviteStatus.PENDING))

    db.session.flush()

    midterm_alice = EventInvitation.query.filter_by(event_id=midterm_review.id, student_id=alice.id).first()
    if midterm_alice:
        midterm_alice.status       = InviteStatus.ACCEPTED
        midterm_alice.responded_at = now

    # ── Messages ─────────────────────────────────────────────
    db.session.add_all([
        Message(group_id=math100.id,    author_id=None,      content="Alice Chen joined the group.",                                                 message_type=MessageType.SYSTEM),
        Message(group_id=math100.id,    author_id=alice.id,  content="Hey everyone! Midterm review session is booked for Thursday — Clearihue A110.", message_type=MessageType.USER),
        Message(group_id=math100.id,    author_id=bob.id,    content="Thanks Alice! I'll be there.",                                                  message_type=MessageType.USER),
        Message(group_id=chess_club.id, author_id=dan.id,    content="Tournament brackets are up — check the events tab!",                            message_type=MessageType.USER),
        Message(group_id=chess_club.id, author_id=eve.id,    content="Can't wait, been practicing all week.",                                         message_type=MessageType.USER),
    ])

    db.session.commit()

    print("✅ Seed complete.")
    print("   Students:  5")
    print("   Groups:    4 (including 1 subgroup)")
    print("   Locations: 6")
    print("   Events:    5 (1 cancelled, 1 recurring, 1 invite-only)")
    print("   Messages:  5")


if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed()
