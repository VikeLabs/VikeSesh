"""
VikeSesh — pytest Test Suite
Tests models, query functions, and Flask routes.

Setup:
    pip install pytest sqlalchemy flask

Run all tests:
    pytest test_models.py -v

Run a specific class:
    pytest test_models.py::TestGetMapPins -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base, Student, Group, CampusLocation, Event, EventInvitation, Message,
    EventVisibility, InviteStatus, MemberRole, MessageType
)
from queries import get_map_pins_for_student, create_event_and_notify, is_group_member


# ── Test Database Setup ───────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """
    Creates a fresh in-memory SQLite database for each test.
    scope=function means every single test gets a completely clean slate —
    no data leaks between tests.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def app_client(db):
    """
    Creates a Flask test client wired to the test database.
    Use this fixture for testing HTTP routes instead of calling
    query functions directly.
    """
    import app as flask_app
    import database

    # Point the app at the test DB session
    flask_app.app.config["TESTING"] = True
    database.SessionLocal = db.__class__

    with flask_app.app.test_client() as client:
        yield client


# ── Reusable Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def two_students(db):
    """Two students already saved to the test DB."""
    alice = Student(uvic_email="alice@uvic.ca", display_name="Alice", student_number="V001")
    bob   = Student(uvic_email="bob@uvic.ca",   display_name="Bob",   student_number="V002")
    db.add_all([alice, bob])
    db.flush()
    return alice, bob


@pytest.fixture
def group_with_members(db, two_students):
    """A group that both test students are members of."""
    alice, bob = two_students
    group = Group(name="MATH 100", course_code="MATH100", is_public=True, created_by=alice.id)
    db.add(group)
    db.flush()
    group.members.append(alice)
    group.members.append(bob)
    db.flush()
    return group, alice, bob


@pytest.fixture
def campus_location(db):
    """A campus location for use in events."""
    loc = CampusLocation(
        name="Clearihue A110", building="Clearihue", room="A110",
        latitude=48.4636, longitude=-123.3117
    )
    db.add(loc)
    db.flush()
    return loc


def make_event(db, group, creator, location, visibility=EventVisibility.PUBLIC_GROUP, cancelled=False):
    """Helper to create a test event with sensible defaults."""
    event = Event(
        title=f"Test Event",
        creator_id=creator.id,
        group_id=group.id,
        location_id=location.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=2),
        visibility=visibility,
        is_cancelled=cancelled,
    )
    db.add(event)
    db.flush()
    return event


# ── Student Model Tests ───────────────────────────────────────────────────────

class TestStudentModel:
    def test_student_created_with_correct_fields(self, db):
        student = Student(uvic_email="test@uvic.ca", display_name="Test User", student_number="V009")
        db.add(student)
        db.flush()
        assert student.id is not None
        assert student.uvic_email == "test@uvic.ca"
        assert student.is_active == True

    def test_student_email_must_be_unique(self, db):
        from sqlalchemy.exc import IntegrityError
        db.add(Student(uvic_email="dup@uvic.ca", display_name="First",  student_number="V010"))
        db.add(Student(uvic_email="dup@uvic.ca", display_name="Second", student_number="V011"))
        with pytest.raises(IntegrityError):
            db.flush()

    def test_student_repr(self, db):
        student = Student(uvic_email="repr@uvic.ca", display_name="Repr Test", student_number="V012")
        db.add(student)
        db.flush()
        assert "Repr Test" in repr(student)
        assert "repr@uvic.ca" in repr(student)


# ── Group Model Tests ─────────────────────────────────────────────────────────

class TestGroupModel:
    def test_group_created_with_defaults(self, db, two_students):
        alice, _ = two_students
        group = Group(name="Chess Club", is_public=True, created_by=alice.id)
        db.add(group)
        db.flush()
        assert group.id is not None
        assert group.is_public == True
        assert group.parent_group_id is None

    def test_student_can_join_group(self, db, two_students):
        alice, bob = two_students
        group = Group(name="MATH 100", is_public=True, created_by=alice.id)
        db.add(group)
        db.flush()
        group.members.append(alice)
        db.flush()
        assert alice in group.members
        assert bob not in group.members

    def test_subgroup_parent_relationship(self, db, two_students):
        alice, _ = two_students
        parent = Group(name="MATH 100",             is_public=True, created_by=alice.id)
        child  = Group(name="MATH 100 — Dr. Smith", is_public=True, created_by=alice.id)
        db.add_all([parent, child])
        db.flush()
        child.parent_group_id = parent.id
        db.flush()
        assert child.parent_group_id == parent.id
        assert child in parent.subgroups

    def test_group_without_course_code(self, db, two_students):
        alice, _ = two_students
        club = Group(name="Rock Climbing Club", course_code=None, is_public=True, created_by=alice.id)
        db.add(club)
        db.flush()
        assert club.course_code is None


# ── Event Model Tests ─────────────────────────────────────────────────────────

class TestEventModel:
    def test_event_created_with_defaults(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location)
        assert event.id is not None
        assert event.is_cancelled == False
        assert event.visibility == EventVisibility.PUBLIC_GROUP

    def test_event_can_be_cancelled(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location)
        event.is_cancelled = True
        db.flush()
        assert event.is_cancelled == True

    def test_event_with_recurrence_rule(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location)
        event.recurrence_rule = "FREQ=WEEKLY;BYDAY=TU;COUNT=10"
        db.flush()
        assert event.recurrence_rule == "FREQ=WEEKLY;BYDAY=TU;COUNT=10"

    def test_invited_only_event(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location, visibility=EventVisibility.INVITED_ONLY)
        assert event.visibility == EventVisibility.INVITED_ONLY


# ── EventInvitation Model Tests ───────────────────────────────────────────────

class TestEventInvitationModel:
    def test_invitation_defaults_to_pending(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = make_event(db, group, alice, campus_location)
        invite = EventInvitation(event_id=event.id, student_id=bob.id)
        db.add(invite)
        db.flush()
        assert invite.status == InviteStatus.PENDING

    def test_invitation_can_be_accepted(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event  = make_event(db, group, alice, campus_location)
        invite = EventInvitation(event_id=event.id, student_id=bob.id)
        db.add(invite)
        db.flush()
        invite.status       = InviteStatus.ACCEPTED
        invite.responded_at = datetime.now(timezone.utc)
        db.flush()
        assert invite.status == InviteStatus.ACCEPTED
        assert invite.responded_at is not None

    def test_invitation_can_be_declined(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event  = make_event(db, group, alice, campus_location)
        invite = EventInvitation(event_id=event.id, student_id=bob.id)
        db.add(invite)
        db.flush()
        invite.status = InviteStatus.DECLINED
        db.flush()
        assert invite.status == InviteStatus.DECLINED


# ── Message Model Tests ───────────────────────────────────────────────────────

class TestMessageModel:
    def test_user_message(self, db, group_with_members):
        group, alice, _ = group_with_members
        msg = Message(group_id=group.id, author_id=alice.id,
                      content="Hello group!", message_type=MessageType.USER)
        db.add(msg)
        db.flush()
        assert msg.id is not None
        assert msg.is_deleted == False
        assert msg.message_type == MessageType.USER

    def test_system_message_has_no_author(self, db, group_with_members):
        group, _, _ = group_with_members
        msg = Message(group_id=group.id, author_id=None,
                      content="Alice joined the group.", message_type=MessageType.SYSTEM)
        db.add(msg)
        db.flush()
        assert msg.author_id is None
        assert msg.message_type == MessageType.SYSTEM

    def test_soft_delete(self, db, group_with_members):
        group, alice, _ = group_with_members
        msg = Message(group_id=group.id, author_id=alice.id,
                      content="To be deleted", message_type=MessageType.USER)
        db.add(msg)
        db.flush()
        msg.is_deleted = True
        db.flush()
        assert msg.is_deleted == True
        assert msg.id is not None  # still exists in DB


# ── Query Function Tests ──────────────────────────────────────────────────────

class TestGetMapPins:
    def test_public_event_visible_to_all_group_members(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = make_event(db, group, alice, campus_location, EventVisibility.PUBLIC_GROUP)
        for member in [alice, bob]:
            db.add(EventInvitation(event_id=event.id, student_id=member.id))
        db.flush()

        assert event in get_map_pins_for_student(alice.id, db)
        assert event in get_map_pins_for_student(bob.id, db)

    def test_invited_only_not_visible_to_uninvited_member(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = make_event(db, group, alice, campus_location, EventVisibility.INVITED_ONLY)
        db.add(EventInvitation(event_id=event.id, student_id=alice.id, invited_by=alice.id))
        db.flush()

        assert event in get_map_pins_for_student(alice.id, db)
        assert event not in get_map_pins_for_student(bob.id, db)

    def test_cancelled_event_not_in_pins(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location, cancelled=True)
        db.add(EventInvitation(event_id=event.id, student_id=alice.id))
        db.flush()
        assert event not in get_map_pins_for_student(alice.id, db)

    def test_declined_invite_not_in_pins(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event  = make_event(db, group, alice, campus_location, EventVisibility.INVITED_ONLY)
        invite = EventInvitation(event_id=event.id, student_id=bob.id,
                                  invited_by=alice.id, status=InviteStatus.DECLINED)
        db.add(invite)
        db.flush()
        assert event not in get_map_pins_for_student(bob.id, db)

    def test_outsider_cannot_see_public_event(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        outsider = Student(uvic_email="outsider@uvic.ca", display_name="Outsider", student_number="V999")
        db.add(outsider)
        db.flush()
        event = make_event(db, group, alice, campus_location)
        db.add(EventInvitation(event_id=event.id, student_id=alice.id))
        db.flush()
        assert event not in get_map_pins_for_student(outsider.id, db)

    def test_empty_pins_for_student_with_no_groups(self, db):
        lonely = Student(uvic_email="lonely@uvic.ca", display_name="Lonely", student_number="V000")
        db.add(lonely)
        db.flush()
        assert get_map_pins_for_student(lonely.id, db) == []

    def test_nonexistent_student_returns_empty(self, db):
        assert get_map_pins_for_student(99999, db) == []


class TestCreateEventAndNotify:
    def test_public_event_invites_all_group_members(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event_data = {
            "title":       "New Event",
            "start_time":  datetime.now(timezone.utc) + timedelta(hours=1),
            "location_id": campus_location.id,
            "visibility":  EventVisibility.PUBLIC_GROUP,
        }
        event = create_event_and_notify(alice.id, group.id, event_data, [], db)
        db.commit()

        invited_ids = {i.student_id for i in db.query(EventInvitation).filter_by(event_id=event.id).all()}
        assert alice.id in invited_ids
        assert bob.id in invited_ids

    def test_invited_only_invites_only_specified_students(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event_data = {
            "title":       "Private Event",
            "start_time":  datetime.now(timezone.utc) + timedelta(hours=1),
            "location_id": campus_location.id,
            "visibility":  EventVisibility.INVITED_ONLY,
        }
        event = create_event_and_notify(alice.id, group.id, event_data, [alice.id], db)
        db.commit()

        invited_ids = {i.student_id for i in db.query(EventInvitation).filter_by(event_id=event.id).all()}
        assert alice.id in invited_ids
        assert bob.id not in invited_ids


class TestIsGroupMember:
    def test_member_returns_true(self, db, group_with_members):
        group, alice, _ = group_with_members
        assert is_group_member(alice.id, group.id, db) == True

    def test_non_member_returns_false(self, db, group_with_members):
        group, _, _ = group_with_members
        outsider = Student(uvic_email="out@uvic.ca", display_name="Out", student_number="V888")
        db.add(outsider)
        db.flush()
        assert is_group_member(outsider.id, group.id, db) == False

    def test_nonexistent_student_returns_false(self, db, group_with_members):
        group, _, _ = group_with_members
        assert is_group_member(99999, group.id, db) == False
