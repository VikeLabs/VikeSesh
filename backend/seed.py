"""
VikeSesh — Seed Script
Populates the database with realistic test data so every developer
can work against a usable local database without entering data manually.

Usage:
    python seed.py

WARNING: This drops and recreates all tables. Never run against production.
"""

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import (
    Base, Student, Group, CampusLocation, Event, EventInvitation,
    Message, EventVisibility, InviteStatus, MemberRole, MessageType,
    group_memberships
)

DATABASE_URL = "sqlite:///vikesesh_test.db"#"postgresql://user:password@localhost/uvic_events"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def seed():
    # Drop all tables and recreate fresh — safe for dev only
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    db = Session()

    # ── Students ─────────────────────────────────────────────────────────────
    alice   = Student(uvic_email="alice@uvic.ca",   display_name="Alice Chen",    student_number="V00111111")
    bob     = Student(uvic_email="bob@uvic.ca",     display_name="Bob Martins",   student_number="V00222222")
    carol   = Student(uvic_email="carol@uvic.ca",   display_name="Carol Singh",   student_number="V00333333")
    dan     = Student(uvic_email="dan@uvic.ca",     display_name="Dan Kowalski",  student_number="V00444444")
    eve     = Student(uvic_email="eve@uvic.ca",     display_name="Eve Thompson",  student_number="V00555555")

    db.add_all([alice, bob, carol, dan, eve])
    db.flush()  # get IDs before creating groups

    # ── Campus Locations ─────────────────────────────────────────────────────
    clearihue   = CampusLocation(name="Clearihue A110",       building="Clearihue",       room="A110", latitude=48.4636, longitude=-123.3117)
    elliot      = CampusLocation(name="Elliott 168",          building="Elliott",         room="168",  latitude=48.4629, longitude=-123.3104)
    library     = CampusLocation(name="McPherson Library",    building="McPherson Library",room=None,  latitude=48.4634, longitude=-123.3096)
    ssc         = CampusLocation(name="Student Union Building",building="SUB",            room=None,   latitude=48.4641, longitude=-123.3131)
    cornett     = CampusLocation(name="Cornett A128",         building="Cornett",         room="A128", latitude=48.4625, longitude=-123.3109)
    petch       = CampusLocation(name="Petch Fountain",       building="Outdoor",         room=None,   latitude=48.4638, longitude=-123.3122)

    db.add_all([clearihue, elliot, library, ssc, cornett, petch])
    db.flush()

    # ── Groups ───────────────────────────────────────────────────────────────
    math100         = Group(name="MATH 100",            course_code="MATH100",  description="Calculus 1 — all sections",      is_public=True,  created_by=alice.id)
    math100_smith   = Group(name="MATH 100 — Dr. Smith",course_code="MATH100",  description="Dr. Smith's Tuesday/Thursday section", is_public=True, created_by=alice.id)
    chess_club      = Group(name="Chess Club",          course_code=None,       description="Weekly chess meetups on campus", is_public=True,  created_by=bob.id)
    bar_crawl       = Group(name="Bar Crawl Nights 2025",course_code=None,      description="Monthly bar crawl crew",         is_public=False, created_by=carol.id)

    db.add_all([math100, chess_club, bar_crawl, math100_smith])
    db.flush()

    # Link subgroup to parent
    math100_smith.parent_group_id = math100.id

    # ── Memberships ──────────────────────────────────────────────────────────
    # Use append() — SQLAlchemy handles the association table insert
    math100.members.append(alice)
    math100.members.append(bob)
    math100.members.append(carol)
    math100_smith.members.append(alice)
    math100_smith.members.append(bob)
    chess_club.members.append(bob)
    chess_club.members.append(dan)
    chess_club.members.append(eve)
    bar_crawl.members.append(carol)
    bar_crawl.members.append(dan)
    bar_crawl.members.append(eve)

    db.flush()

    # ── Events ───────────────────────────────────────────────────────────────
    now = datetime.utcnow()

    # Public group event — all MATH 100 members see this pin
    midterm_review = Event(
        title="MATH 100 Midterm Review",
        description="Group study session before the midterm. Bring practice problems.",
        creator_id=alice.id,
        group_id=math100.id,
        location_id=clearihue.id,
        start_time=now + timedelta(days=2, hours=14),
        end_time=now + timedelta(days=2, hours=16),
        visibility=EventVisibility.PUBLIC_GROUP,
    )

    # Recurring weekly study group
    weekly_study = Event(
        title="Weekly MATH 100 Study Group",
        description="Every Tuesday at the library. All welcome.",
        creator_id=bob.id,
        group_id=math100.id,
        location_id=library.id,
        start_time=now + timedelta(days=1, hours=13),
        end_time=now + timedelta(days=1, hours=15),
        visibility=EventVisibility.PUBLIC_GROUP,
        recurrence_rule="FREQ=WEEKLY;BYDAY=TU;COUNT=10",  # 10 weeks of Tuesdays
    )

    # Invite-only event — only carol and dan see this pin
    bar_crawl_event = Event(
        title="October Bar Crawl",
        description="Starting at the Grad House, ending wherever.",
        creator_id=carol.id,
        group_id=bar_crawl.id,
        location_id=ssc.id,
        start_time=now + timedelta(days=5, hours=21),
        end_time=now + timedelta(days=5, hours=23, minutes=59),
        visibility=EventVisibility.INVITED_ONLY,
    )

    # Chess tournament — public to chess club members
    chess_tournament = Event(
        title="Chess Club Tournament",
        description="Single elimination. Bring your own clock if you have one.",
        creator_id=dan.id,
        group_id=chess_club.id,
        location_id=cornett.id,
        start_time=now + timedelta(days=3, hours=10),
        end_time=now + timedelta(days=3, hours=13),
        visibility=EventVisibility.PUBLIC_GROUP,
    )

    # A cancelled event (tests that cancelled events don't show as map pins)
    cancelled_event = Event(
        title="Cancelled Study Session",
        description="This was cancelled.",
        creator_id=alice.id,
        group_id=math100.id,
        location_id=elliot.id,
        start_time=now + timedelta(days=1),
        visibility=EventVisibility.PUBLIC_GROUP,
        is_cancelled=True,
    )

    db.add_all([midterm_review, weekly_study, bar_crawl_event, chess_tournament, cancelled_event])
    db.flush()

    # ── Invitations ──────────────────────────────────────────────────────────
    # Public events: auto-invite all group members
    for event, group in [(midterm_review, math100), (weekly_study, math100), (chess_tournament, chess_club)]:
        for member in group.members:
            db.add(EventInvitation(
                event_id=event.id,
                student_id=member.id,
                invited_by=None,  # system-generated
                status=InviteStatus.PENDING,
            ))

    # Invite-only bar crawl: only carol and dan invited
    for student in [carol, dan]:
        db.add(EventInvitation(
            event_id=bar_crawl_event.id,
            student_id=student.id,
            invited_by=carol.id,
            status=InviteStatus.PENDING,
        ))

    # Alice accepts the midterm review
    midterm_alice = db.query(EventInvitation).filter_by(
        event_id=midterm_review.id, student_id=alice.id
    ).first()
    if midterm_alice:
        midterm_alice.status = InviteStatus.ACCEPTED
        midterm_alice.responded_at = datetime.utcnow()

    # ── Messages ─────────────────────────────────────────────────────────────
    db.add_all([
        Message(group_id=math100.id, author_id=None,      content="Alice Chen joined the group.",          message_type=MessageType.SYSTEM),
        Message(group_id=math100.id, author_id=alice.id,  content="Hey everyone! Midterm review session is booked for Thursday — Clearihue A110.", message_type=MessageType.USER),
        Message(group_id=math100.id, author_id=bob.id,    content="Thanks Alice! I'll be there.",           message_type=MessageType.USER),
        Message(group_id=chess_club.id, author_id=dan.id, content="Tournament brackets are up — check the events tab!", message_type=MessageType.USER),
        Message(group_id=chess_club.id, author_id=eve.id, content="Can't wait, been practicing all week.",  message_type=MessageType.USER),
    ])

    db.commit()
    db.close()
    print("✅ Seed complete.")
    print(f"   Students:  5")
    print(f"   Groups:    4 (including 1 subgroup)")
    print(f"   Locations: 6")
    print(f"   Events:    5 (1 cancelled, 1 recurring, 1 invite-only)")
    print(f"   Messages:  5")

if __name__ == "__main__":
    seed()
