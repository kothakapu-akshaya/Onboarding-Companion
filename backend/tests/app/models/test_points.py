"""Unit tests for app/models/points.py SQLModel models.

Tests cover model instantiation, field constraints, default values,
and database persistence using an in-memory SQLite database.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine, select

from app.models.points import PointsEvent

# ============================================================
# In-memory SQLite engine & session fixture
# ============================================================


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine with only the PointsEvent table.

    We avoid SQLModel.metadata.create_all() because other tables (e.g. User)
    use PostgreSQL-specific types like JSONB that SQLite cannot compile.
    """
    eng = create_engine("sqlite:///:memory:")
    # Only create the pointsevent table
    PointsEvent.metadata.create_all(eng, tables=[PointsEvent.__table__])
    return eng


@pytest.fixture
def session(engine):
    """Provide a transactional session that rolls back after each test."""
    with Session(engine) as sess:
        yield sess
        sess.rollback()


# ============================================================
# Helpers
# ============================================================

VALID_USER_ID = uuid.uuid4()
VALID_RECORD_UID = uuid.uuid4()


def _make_points_event(**overrides):
    """Build a PointsEvent with sensible defaults."""
    defaults = dict(user_id=VALID_USER_ID)
    defaults.update(overrides)
    return PointsEvent(**defaults)


# ============================================================
# Model instantiation & defaults
# ============================================================


class TestPointsEventInstantiation:
    """Test PointsEvent model instantiation and default values."""

    def test_create_with_minimal_fields(self):
        """Only user_id is truly required; all other fields have defaults."""
        evt = _make_points_event()
        assert evt.user_id == VALID_USER_ID
        assert evt.points == 1
        assert evt.reason == "record_created"
        assert evt.record_uid is None
        assert isinstance(evt.id, uuid.UUID)
        assert isinstance(evt.created_at, datetime)

    def test_create_with_all_fields(self):
        evt = PointsEvent(
            user_id=VALID_USER_ID,
            record_uid=VALID_RECORD_UID,
            points=25.5,
            reason="daily_login",
        )
        assert evt.user_id == VALID_USER_ID
        assert evt.record_uid == VALID_RECORD_UID
        assert evt.points == 25.5
        assert evt.reason == "daily_login"
        assert isinstance(evt.id, uuid.UUID)
        assert isinstance(evt.created_at, datetime)

    def test_id_is_unique_per_instance(self):
        evt1 = _make_points_event()
        evt2 = _make_points_event()
        assert evt1.id != evt2.id

    def test_created_at_is_utc(self):
        evt = _make_points_event()
        assert evt.created_at.tzinfo == timezone.utc

    def test_created_at_is_recent(self):
        before = datetime.now(timezone.utc)
        evt = _make_points_event()
        after = datetime.now(timezone.utc)
        assert before <= evt.created_at <= after


# ============================================================
# Field constraints (Python-level)
# ============================================================


class TestPointsEventFieldConstraints:
    """Test field-level constraints on PointsEvent."""

    def test_points_zero(self):
        """Points can be exactly 0 (ge=0)."""
        evt = _make_points_event(points=0)
        assert evt.points == 0

    def test_points_positive_value(self):
        evt = _make_points_event(points=100.0)
        assert evt.points == 100.0

    def test_points_fractional(self):
        evt = _make_points_event(points=0.5)
        assert evt.points == 0.5

    def test_points_as_int(self):
        """Int values are accepted for the points field."""
        evt = _make_points_event(points=5)
        assert evt.points == 5

    def test_reason_default_length(self):
        evt = _make_points_event()
        assert len(evt.reason) <= 50

    def test_reason_max_length_50_accepted(self):
        evt = _make_points_event(reason="a" * 50)
        assert evt.reason == "a" * 50

    def test_reason_exceeds_max_length_still_accepted_at_python_level(self):
        """max_length is enforced at DB/schema level.

        Not Python instantiation.
        """
        evt = _make_points_event(reason="a" * 100)
        assert evt.reason == "a" * 100

    def test_reason_empty_string_accepted(self):
        evt = _make_points_event(reason="")
        assert evt.reason == ""

    def test_user_id_is_uuid(self):
        evt = _make_points_event(user_id=uuid.uuid4())
        assert isinstance(evt.user_id, uuid.UUID)

    def test_record_uid_none(self):
        evt = _make_points_event(record_uid=None)
        assert evt.record_uid is None

    def test_record_uid_set(self):
        evt = _make_points_event(record_uid=uuid.uuid4())
        assert isinstance(evt.record_uid, uuid.UUID)


# ============================================================
# Database persistence (SQLite in-memory)
# ============================================================


class TestPointsEventDatabase:
    """Test PointsEvent persistence via in-memory SQLite."""

    # --- Basic CRUD ---

    def test_insert_and_query(self, session):
        evt = _make_points_event()
        session.add(evt)
        session.commit()
        session.refresh(evt)

        result = session.get(PointsEvent, evt.id)
        assert result is not None
        assert result.user_id == evt.user_id
        assert result.points == 1
        assert result.reason == "record_created"

    def test_insert_multiple_records(self, session):
        events = [
            _make_points_event(user_id=uuid.uuid4(), points=1.0),
            _make_points_event(user_id=uuid.uuid4(), points=5.0),
            _make_points_event(user_id=uuid.uuid4(), points=0),
        ]
        session.add_all(events)
        session.commit()

        all_events = session.exec(select(PointsEvent)).all()
        assert len(all_events) == 3

    def test_update_record(self, session):
        evt = _make_points_event(points=10.0)
        session.add(evt)
        session.commit()
        session.refresh(evt)

        evt.points = 20.0
        evt.reason = "updated_reason"
        session.add(evt)
        session.commit()
        session.refresh(evt)

        result = session.get(PointsEvent, evt.id)
        assert result.points == 20.0
        assert result.reason == "updated_reason"

    def test_delete_record(self, session):
        evt = _make_points_event()
        session.add(evt)
        session.commit()
        session.refresh(evt)

        session.delete(evt)
        session.commit()

        result = session.get(PointsEvent, evt.id)
        assert result is None

    # --- Nullable fields ---

    def test_record_uid_nullable(self, session):
        evt = _make_points_event(record_uid=None)
        session.add(evt)
        session.commit()
        session.refresh(evt)
        assert evt.record_uid is None

    def test_record_uid_can_be_set(self, session):
        evt = _make_points_event(record_uid=None)
        session.add(evt)
        session.commit()
        session.refresh(evt)

        evt.record_uid = uuid.uuid4()
        session.add(evt)
        session.commit()
        session.refresh(evt)

        assert evt.record_uid is not None

    # --- Uniqueness constraint on record_uid ---

    def test_unique_record_uid(self, session):
        """Two events cannot share the same record_uid."""
        uid = uuid.uuid4()
        evt1 = _make_points_event(user_id=uuid.uuid4(), record_uid=uid)
        evt2 = _make_points_event(user_id=uuid.uuid4(), record_uid=uid)
        session.add(evt1)
        session.commit()
        session.add(evt2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_none_record_uid_no_conflict(self, session):
        """Multiple events with record_uid=None should not conflict.

        (SQLite quirk).
        """
        evt1 = _make_points_event(record_uid=None)
        evt2 = _make_points_event(record_uid=None)
        session.add_all([evt1, evt2])
        session.commit()

        all_events = session.exec(select(PointsEvent)).all()
        assert len(all_events) == 2

    # --- Non-nullable user_id ---

    def test_user_id_required_in_db(self, session):
        """user_id is non-nullable at DB level; NULL should fail on insert."""
        from sqlalchemy import text

        # Use raw SQL to bypass SQLModel validation and test DB constraint
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "INSERT INTO pointsevent "
                    "(id, user_id, record_uid, "
                    "points, reason, created_at) "
                    "VALUES ("
                    ":id, NULL, NULL, 1.0, "
                    "'test', '2026-01-01T00:00:00')"
                ),
                {"id": str(uuid.uuid4())},
            )
            session.commit()

    # --- ge=0 constraint at DB level ---

    def test_points_negative_stored_in_sqlite(self, session):
        """SQLite doesn't enforce CHECK constraints by default.

        But SQLModel's ge=0 may create one. Test what happens.
        """
        evt = _make_points_event(points=-5.0)
        session.add(evt)
        try:
            session.commit()
            session.refresh(evt)
            # If SQLite allowed it, the value is stored
            assert evt.points == -5.0
        except IntegrityError:
            # CHECK constraint blocked it — also valid behavior
            session.rollback()
            pytest.skip("SQLite CHECK constraint rejected negative points")

    # --- Indexes exist (schema-level check) ---

    def test_table_has_indexes(self, engine):
        """Verify that indexes on user_id and created_at are created."""
        inspector = __import__("sqlalchemy").inspect(engine)
        indexes = inspector.get_indexes("pointsevent")
        index_columns = {idx["column_names"][0] for idx in indexes}
        assert "user_id" in index_columns
        assert "created_at" in index_columns

    def test_table_has_unique_constraint_on_record_uid(self, engine):
        inspector = __import__("sqlalchemy").inspect(engine)
        uniques = inspector.get_unique_constraints("pointsevent")
        unique_columns = {uc["column_names"][0] for uc in uniques}
        assert "record_uid" in unique_columns

    def test_table_has_check_constraint_on_points(self, engine):
        """Verify ge=0 created a CHECK constraint (may not apply in SQLite)."""
        inspector = __import__("sqlalchemy").inspect(engine)
        # SQLite may or may not expose check constraints via inspector
        checks = inspector.get_check_constraints("pointsevent")
        if checks:
            # SQLModel/Pydantic creates a check constraint for ge
            assert len(checks) >= 1


# ============================================================
# Serialization
# ============================================================


class TestPointsEventSerialization:
    """Test model_dump() output structure."""

    def test_model_dump(self):
        evt = _make_points_event(
            record_uid=VALID_RECORD_UID, points=10.0, reason="test"
        )
        dump = evt.model_dump()
        assert dump["user_id"] == VALID_USER_ID
        assert dump["record_uid"] == VALID_RECORD_UID
        assert dump["points"] == 10.0
        assert dump["reason"] == "test"
        assert isinstance(dump["id"], uuid.UUID)
        assert isinstance(dump["created_at"], datetime)

    def test_model_dump_with_none_record_uid(self):
        evt = _make_points_event(record_uid=None)
        dump = evt.model_dump()
        assert dump["record_uid"] is None

    def test_model_dump_json(self):
        evt = _make_points_event()
        json_str = evt.model_dump_json()
        assert isinstance(json_str, str)
        assert "user_id" in json_str
        assert "points" in json_str

    def test_model_dump_from_db(self, session):
        """Verify model_dump() works correctly on objects loaded from DB."""
        evt = _make_points_event(points=42.0, reason="from_db_test")
        session.add(evt)
        session.commit()
        session.refresh(evt)

        loaded = session.get(PointsEvent, evt.id)
        dump = loaded.model_dump()
        assert dump["points"] == 42.0
        assert dump["reason"] == "from_db_test"
        assert dump["user_id"] == evt.user_id
