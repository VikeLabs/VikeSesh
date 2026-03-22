"""
VikeSesh — pytest Test Suite
Tests models and core query functions using Flask-SQLAlchemy.

Setup:
    pip install pytest flask flask-sqlalchemy

Run all tests:
    pytest backend/test_models.py -v

Run a specific class:
    pytest backend/test_models.py::TestGetMapPins -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from backend.app import create_app
from backend.extensions import db as _db
from backend.models import (
    Student, Group, CampusLocation, Event, EventInvitation, Message,
    EventVisibility, InviteStatus, MessageType
)
from backend.queries import get_map_pins_for_student, create_event_and_notify, is_group_member


@pytest.fixture(scope="session")
def app():
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    return test_app


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def two_students(db):
    alice = Student(email="alice@uvic.ca", password_hash="hashed", display_name="Alice", student_number="V001", is_verified=True)
    bob   = Student(email="bob@uvic.ca",   password_hash="hashed", display_name="Bob",   student_number="V002", is_verified=True)
    db.session.add_all([alice, bob])
    db.session.flush()
    return alice, bob


@pytest.fixture
def group_with_members(db, two_students):
    alice, bob = two_students
    group = Group(name="MATH 100", course_code="MATH100", is_public=True, created_by=alice.id)
    db.session.add(group)
    db.session.flush()
    group.members.append(alice)
    group.members.append(bob)
    db.session.flush()
    return group, alice, bob


@pytest.fixture
def campus_location(db):
    loc = CampusLocation(name="Clearihue A110", building="Clearihue", room="A110", latitude=48.4636, longitude=-123.3117)
    db.session.add(loc)
    db.session.flush()
    return loc


def make_event(db, group, creator, location, visibility=EventVisibility.PUBLIC_GROUP, cancelled=False):
    event = Event(
        title="Test Event",
        creator_id=creator.id,
        group_id=group.id,
        location_id=location.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=2),
        visibility=visibility,
        is_cancelled=cancelled,
    )
    db.session.add(event)
    db.session.flush()
    return event


class TestStudentModel:
    def test_student_created_with_correct_fields(self, db):
        student = Student(email="test@uvic.ca", password_hash="hashed", display_name="Test User", student_number="V009", is_verified=False)
        db.session.add(student)
        db.session.flush()
        assert student.id is not None
        assert student.is_active == True
        assert student.is_verified == False

    def test_student_email_must_be_unique(self, db):
        from sqlalchemy.exc import IntegrityError
        db.session.add(Student(email="dup@uvic.ca", password_hash="h", display_name="First",  student_number="V010", is_verified=True))
        db.session.add(Student(email="dup@uvic.ca", password_hash="h", display_name="Second", student_number="V011", is_verified=True))
        with pytest.raises(IntegrityError):
            db.session.flush()

    def test_student_repr(self, db):
        student = Student(email="repr@uvic.ca", password_hash="h", display_name="Repr Test", student_number="V012", is_verified=True)
        db.session.add(student)
        db.session.flush()
        assert "Repr Test" in repr(student)


class TestGroupModel:
    def test_group_created_with_defaults(self, db, two_students):
        alice, _ = two_students
        group = Group(name="Chess Club", is_public=True, created_by=alice.id)
        db.session.add(group)
        db.session.flush()
        assert group.id is not None
        assert group.parent_group_id is None

    def test_student_can_join_group(self, db, two_students):
        alice, bob = two_students
        group = Group(name="MATH 100", is_public=True, created_by=alice.id)
        db.session.add(group)
        db.session.flush()
        group.members.append(alice)
        db.session.flush()
        assert alice in group.members
        assert bob not in group.members

    def test_subgroup_parent_relationship(self, db, two_students):
        alice, _ = two_students
        parent = Group(name="MATH 100",             is_public=True, created_by=alice.id)
        child  = Group(name="MATH 100 - Dr. Smith", is_public=True, created_by=alice.id)
        db.session.add_all([parent, child])
        db.session.flush()
        child.parent_group_id = parent.id
        db.session.flush()
        assert child in parent.subgroups


class TestEventModel:
    def test_event_created_with_defaults(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location)
        assert event.id is not None
        assert event.is_cancelled == False

    def test_event_can_be_cancelled(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location)
        event.is_cancelled = True
        db.session.flush()
        assert event.is_cancelled == True

    def test_event_with_recurrence_rule(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location)
        event.recurrence_rule = "FREQ=WEEKLY;BYDAY=TU;COUNT=10"
        db.session.flush()
        assert event.recurrence_rule == "FREQ=WEEKLY;BYDAY=TU;COUNT=10"


class TestEventInvitationModel:
    def test_invitation_defaults_to_pending(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event  = make_event(db, group, alice, campus_location)
        invite = EventInvitation(event_id=event.id, student_id=bob.id)
        db.session.add(invite)
        db.session.flush()
        assert invite.status == InviteStatus.PENDING

    def test_invitation_can_be_accepted(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event  = make_event(db, group, alice, campus_location)
        invite = EventInvitation(event_id=event.id, student_id=bob.id)
        db.session.add(invite)
        db.session.flush()
        invite.status       = InviteStatus.ACCEPTED
        invite.responded_at = datetime.now(timezone.utc)
        db.session.flush()
        assert invite.status == InviteStatus.ACCEPTED


class TestMessageModel:
    def test_user_message(self, db, group_with_members):
        group, alice, _ = group_with_members
        msg = Message(group_id=group.id, author_id=alice.id, content="Hello!", message_type=MessageType.USER)
        db.session.add(msg)
        db.session.flush()
        assert msg.id is not None
        assert msg.is_deleted == False

    def test_system_message_has_no_author(self, db, group_with_members):
        group, _, _ = group_with_members
        msg = Message(group_id=group.id, author_id=None, content="Alice joined.", message_type=MessageType.SYSTEM)
        db.session.add(msg)
        db.session.flush()
        assert msg.author_id is None


class TestGetMapPins:
    def test_public_event_visible_to_all_group_members(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = make_event(db, group, alice, campus_location, EventVisibility.PUBLIC_GROUP)
        for member in [alice, bob]:
            db.session.add(EventInvitation(event_id=event.id, student_id=member.id))
        db.session.flush()
        assert event in get_map_pins_for_student(alice.id)
        assert event in get_map_pins_for_student(bob.id)

    def test_invited_only_not_visible_to_uninvited(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = make_event(db, group, alice, campus_location, EventVisibility.INVITED_ONLY)
        db.session.add(EventInvitation(event_id=event.id, student_id=alice.id, invited_by=alice.id))
        db.session.flush()
        assert event in get_map_pins_for_student(alice.id)
        assert event not in get_map_pins_for_student(bob.id)

    def test_cancelled_event_not_in_pins(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = make_event(db, group, alice, campus_location, cancelled=True)
        db.session.add(EventInvitation(event_id=event.id, student_id=alice.id))
        db.session.flush()
        assert event not in get_map_pins_for_student(alice.id)

    def test_declined_invite_not_in_pins(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event  = make_event(db, group, alice, campus_location, EventVisibility.INVITED_ONLY)
        invite = EventInvitation(event_id=event.id, student_id=bob.id, invited_by=alice.id, status=InviteStatus.DECLINED)
        db.session.add(invite)
        db.session.flush()
        assert event not in get_map_pins_for_student(bob.id)

    def test_outsider_cannot_see_public_event(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        outsider = Student(email="out@uvic.ca", password_hash="h", display_name="Outsider", student_number="V999", is_verified=True)
        db.session.add(outsider)
        db.session.flush()
        event = make_event(db, group, alice, campus_location)
        db.session.add(EventInvitation(event_id=event.id, student_id=alice.id))
        db.session.flush()
        assert event not in get_map_pins_for_student(outsider.id)

    def test_empty_pins_for_student_with_no_groups(self, db):
        lonely = Student(email="lonely@uvic.ca", password_hash="h", display_name="Lonely", student_number="V000", is_verified=True)
        db.session.add(lonely)
        db.session.flush()
        assert get_map_pins_for_student(lonely.id) == []

    def test_nonexistent_student_returns_empty(self, db):
        assert get_map_pins_for_student(99999) == []


class TestIsGroupMember:
    def test_member_returns_true(self, db, group_with_members):
        group, alice, _ = group_with_members
        assert is_group_member(alice.id, group.id) == True

    def test_non_member_returns_false(self, db, group_with_members):
        group, _, _ = group_with_members
        outsider = Student(email="out2@uvic.ca", password_hash="h", display_name="Out", student_number="V888", is_verified=True)
        db.session.add(outsider)
        db.session.flush()
        assert is_group_member(outsider.id, group.id) == False

    def test_nonexistent_student_returns_false(self, db, group_with_members):
        group, _, _ = group_with_members
        assert is_group_member(99999, group.id) == False
