"""
VikeSesh — pytest Test Suite
Tests the database models and core query functions.

Setup:
    pip install pytest sqlalchemy

Run:
    pytest test_models.py -v

These tests use an in-memory SQLite database so they run fast
and never touch your real PostgreSQL database.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base, Student, Group, CampusLocation, Event, EventInvitation, Message,
    EventVisibility, InviteStatus, MemberRole, MessageType
)
from queries_and_routes import get_map_pins_for_student, create_event_and_notify


# ── Test Database Setup ───────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """
    Creates a fresh in-memory SQLite database for each test function.
    'scope=function' means every single test gets a clean slate —
    no data leaks between tests.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


# ── Fixtures: reusable test data ──────────────────────────────────────────────

@pytest.fixture
def two_students(db):
    """Returns two students already saved to the test DB."""
    alice = Student(uvic_email="alice@uvic.ca", display_name="Alice", student_number="V001")
    bob   = Student(uvic_email="bob@uvic.ca",   display_name="Bob",   student_number="V002")
    db.add_all([alice, bob])
    db.flush()
    return alice, bob


@pytest.fixture
def group_with_members(db, two_students):
    """Returns a group that both test students are members of."""
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
    """Returns a campus location for use in events."""
    loc = CampusLocation(name="Clearihue A110", building="Clearihue", room="A110", latitude=48.4636, longitude=-123.3117)
    db.add(loc)
    db.flush()
    return loc


# ── Model Tests ───────────────────────────────────────────────────────────────

class TestStudentModel:
    def test_student_created_with_correct_fields(self, db):
        student = Student(uvic_email="test@uvic.ca", display_name="Test User", student_number="V009")
        db.add(student)
        db.flush()
        assert student.id is not None
        assert student.uvic_email == "test@uvic.ca"
        assert student.is_active == True  # default value

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


class TestGroupModel:
    def test_group_created_with_defaults(self, db, two_students):
        alice, _ = two_students
        group = Group(name="Chess Club", is_public=True, created_by=alice.id)
        db.add(group)
        db.flush()
        assert group.id is not None
        assert group.is_public == True
        assert group.parent_group_id is None  # no parent by default

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
        parent = Group(name="MATH 100",              is_public=True, created_by=alice.id)
        child  = Group(name="MATH 100 — Dr. Smith",  is_public=True, created_by=alice.id)
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


class TestEventModel:
    def test_event_created_with_defaults(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = Event(
            title="Study Session",
            creator_id=alice.id,
            group_id=group.id,
            location_id=campus_location.id,
            start_time=datetime.utcnow() + timedelta(hours=2),
            visibility=EventVisibility.PUBLIC_GROUP,
        )
        db.add(event)
        db.flush()
        assert event.id is not None
        assert event.is_cancelled == False
        assert event.visibility == EventVisibility.PUBLIC_GROUP

    def test_event_can_be_cancelled(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = Event(title="Cancelled", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.PUBLIC_GROUP)
        db.add(event)
        db.flush()
        event.is_cancelled = True
        db.flush()
        assert event.is_cancelled == True

    def test_event_with_recurrence_rule(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = Event(
            title="Weekly Study",
            creator_id=alice.id,
            group_id=group.id,
            location_id=campus_location.id,
            start_time=datetime.utcnow(),
            visibility=EventVisibility.PUBLIC_GROUP,
            recurrence_rule="FREQ=WEEKLY;BYDAY=TU;COUNT=10",
        )
        db.add(event)
        db.flush()
        assert event.recurrence_rule == "FREQ=WEEKLY;BYDAY=TU;COUNT=10"

    def test_invited_only_event(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        event = Event(title="Secret Meetup", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.INVITED_ONLY)
        db.add(event)
        db.flush()
        assert event.visibility == EventVisibility.INVITED_ONLY


class TestEventInvitationModel:
    def test_invitation_defaults_to_pending(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = Event(title="Test Event", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.PUBLIC_GROUP)
        db.add(event)
        db.flush()
        invite = EventInvitation(event_id=event.id, student_id=bob.id)
        db.add(invite)
        db.flush()
        assert invite.status == InviteStatus.PENDING

    def test_invitation_can_be_accepted(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = Event(title="Test Event", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.PUBLIC_GROUP)
        db.add(event)
        db.flush()
        invite = EventInvitation(event_id=event.id, student_id=bob.id)
        db.add(invite)
        db.flush()
        invite.status = InviteStatus.ACCEPTED
        invite.responded_at = datetime.utcnow()
        db.flush()
        assert invite.status == InviteStatus.ACCEPTED
        assert invite.responded_at is not None


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


# ── Query Function Tests ──────────────────────────────────────────────────────

class TestGetMapPins:
    """Tests for the core get_map_pins_for_student query."""

    def test_public_event_visible_to_all_group_members(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = Event(title="Public Event", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.PUBLIC_GROUP)
        db.add(event)
        db.flush()
        # Auto-invite both members
        for member in [alice, bob]:
            db.add(EventInvitation(event_id=event.id, student_id=member.id))
        db.flush()

        # Both should see the pin
        alice_pins = get_map_pins_for_student(alice.id, db)
        bob_pins   = get_map_pins_for_student(bob.id, db)
        assert event in alice_pins
        assert event in bob_pins

    def test_invited_only_event_not_visible_to_uninvited_member(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = Event(title="Private Event", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.INVITED_ONLY)
        db.add(event)
        db.flush()
        # Only invite alice, not bob
        db.add(EventInvitation(event_id=event.id, student_id=alice.id, invited_by=alice.id))
        db.flush()

        alice_pins = get_map_pins_for_student(alice.id, db)
        bob_pins   = get_map_pins_for_student(bob.id, db)
        assert event in alice_pins
        assert event not in bob_pins  # bob was not invited

    def test_cancelled_event_not_in_pins(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = Event(title="Cancelled", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.PUBLIC_GROUP, is_cancelled=True)
        db.add(event)
        db.flush()
        db.add(EventInvitation(event_id=event.id, student_id=alice.id))
        db.flush()

        pins = get_map_pins_for_student(alice.id, db)
        assert event not in pins

    def test_declined_invite_not_in_pins(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event = Event(title="Declined Event", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.INVITED_ONLY)
        db.add(event)
        db.flush()
        invite = EventInvitation(event_id=event.id, student_id=bob.id,
                                  invited_by=alice.id, status=InviteStatus.DECLINED)
        db.add(invite)
        db.flush()

        pins = get_map_pins_for_student(bob.id, db)
        assert event not in pins

    def test_student_not_in_group_cannot_see_public_event(self, db, group_with_members, campus_location):
        group, alice, _ = group_with_members
        # Create a third student who is NOT in the group
        outsider = Student(uvic_email="outsider@uvic.ca", display_name="Outsider", student_number="V999")
        db.add(outsider)
        db.flush()

        event = Event(title="Group Event", creator_id=alice.id, group_id=group.id,
                      location_id=campus_location.id, start_time=datetime.utcnow(),
                      visibility=EventVisibility.PUBLIC_GROUP)
        db.add(event)
        db.flush()
        db.add(EventInvitation(event_id=event.id, student_id=alice.id))
        db.flush()

        pins = get_map_pins_for_student(outsider.id, db)
        assert event not in pins

    def test_empty_pins_for_student_with_no_groups(self, db):
        lonely = Student(uvic_email="lonely@uvic.ca", display_name="Lonely", student_number="V000")
        db.add(lonely)
        db.flush()
        pins = get_map_pins_for_student(lonely.id, db)
        assert pins == []


class TestCreateEventAndNotify:
    def test_public_event_invites_all_group_members(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event_data = {
            "title": "New Event",
            "start_time": datetime.utcnow() + timedelta(hours=1),
            "location_id": campus_location.id,
            "visibility": EventVisibility.PUBLIC_GROUP,
        }
        event = create_event_and_notify(alice.id, group.id, event_data, [], db)
        invites = db.query(EventInvitation).filter_by(event_id=event.id).all()
        invited_ids = {i.student_id for i in invites}
        assert alice.id in invited_ids
        assert bob.id in invited_ids

    def test_invited_only_event_invites_only_specified_students(self, db, group_with_members, campus_location):
        group, alice, bob = group_with_members
        event_data = {
            "title": "Private Event",
            "start_time": datetime.utcnow() + timedelta(hours=1),
            "location_id": campus_location.id,
            "visibility": EventVisibility.INVITED_ONLY,
        }
        # Only invite alice
        event = create_event_and_notify(alice.id, group.id, event_data, [alice.id], db)
        invites = db.query(EventInvitation).filter_by(event_id=event.id).all()
        invited_ids = {i.student_id for i in invites}
        assert alice.id in invited_ids
        assert bob.id not in invited_ids  # bob not explicitly invited
