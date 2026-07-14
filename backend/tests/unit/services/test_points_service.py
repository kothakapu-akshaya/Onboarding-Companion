"""Tests for points_service - awarding points for records and edits."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock
from uuid import uuid4

from app.models.points import PointsEvent
from app.models.record import Record
from app.services.points_service import award_for_edit, award_for_record


class TestAwardForRecord:
    """Tests for award_for_record function."""

    def test_award_for_record_success(
        self, db_session, test_user, test_category
    ):
        """Test successful points award for new record."""
        record = Record(
            uid=uuid4(),
            title="Test Record Title Here",
            description=(
                "This is a test record description with enough characters."
            ),
            user_id=test_user.id,
            category_ids=[str(test_category.id)],
            media_type="text",
            release_rights="creator",
            language="en",
            status="uploaded",
        )
        db_session.add(record)
        db_session.commit()

        award_for_record(db_session, record)

        events = db_session.exec(
            db_session.query(PointsEvent).where(
                PointsEvent.record_uid == record.uid
            )
        ).all()
        assert len(events) == 1
        assert events[0].points == 1.1

    def test_award_for_record_no_user_id(self, db_session):
        """Test no points awarded when record has no user_id."""
        record = Record(
            uid=uuid4(),
            title="Test Record Title Here",
            description=(
                "This is a test record description with enough characters."
            ),
            user_id=None,
            media_type="text",
            release_rights="creator",
            language="en",
        )

        award_for_record(db_session, record)

        events = db_session.exec(
            db_session.query(PointsEvent).where(
                PointsEvent.record_uid == record.uid
            )
        ).all()
        assert len(events) == 0

    def test_award_for_record_no_uid(self, db_session, test_user):
        """Test no points awarded when record has no uid."""
        record = Record(
            uid=None,
            title="Test Record Title Here",
            description=(
                "This is a test record description with enough characters."
            ),
            user_id=test_user.id,
            media_type="text",
            release_rights="creator",
            language="en",
        )

        award_for_record(db_session, record)

        events = db_session.exec(db_session.query(PointsEvent)).all()
        assert len(events) == 0

    def test_award_for_record_idempotent(
        self, db_session, test_user, test_category
    ):
        """Test that points are only awarded once per record."""
        record = Record(
            uid=uuid4(),
            title="Test Record Title Here",
            description=(
                "This is a test record description with enough characters."
            ),
            user_id=test_user.id,
            category_ids=[str(test_category.id)],
            media_type="text",
            release_rights="creator",
            language="en",
            status="uploaded",
        )
        db_session.add(record)
        db_session.commit()

        award_for_record(db_session, record)
        award_for_record(db_session, record)

        events = db_session.exec(
            db_session.query(PointsEvent).where(
                PointsEvent.record_uid == record.uid
            )
        ).all()
        assert len(events) == 1

    def test_award_for_record_with_active_streak(
        self, db_session, test_user, test_category
    ):
        """Test points with active streak increases multiplier."""
        test_user.streak_multiplier = 1.5
        test_user.streak_expires_at = datetime.now(timezone.utc) + timedelta(
            hours=12
        )
        db_session.add(test_user)
        db_session.commit()

        record = Record(
            uid=uuid4(),
            title="Test Record Title Here",
            description=(
                "This is a test record description with enough characters."
            ),
            user_id=test_user.id,
            category_ids=[str(test_category.id)],
            media_type="text",
            release_rights="creator",
            language="en",
            status="uploaded",
        )
        db_session.add(record)
        db_session.commit()

        award_for_record(db_session, record)

        db_session.refresh(test_user)
        assert test_user.streak_multiplier == 1.6


class TestAwardForEdit:
    """Tests for award_for_edit function."""

    def test_award_for_edit_success(self, db_session, test_user, test_record):
        """Test successful points award for editing record."""
        test_user.streak_multiplier = 1.0
        db_session.add(test_user)
        db_session.commit()

        award_for_edit(db_session, test_record, test_user.id)

        events = db_session.exec(
            db_session.query(PointsEvent).where(
                PointsEvent.reason == "record_edited"
            )
        ).all()
        assert len(events) == 1
        assert events[0].points == 1.0

    def test_award_for_edit_no_record_uid(self, db_session, test_user):
        """Test no points when record has no uid."""
        record = Record(
            uid=None,
            title="Test Record Title Here",
            description=(
                "This is a test record description with enough characters."
            ),
            user_id=test_user.id,
            media_type="text",
            release_rights="creator",
            language="en",
        )

        award_for_edit(db_session, record, test_user.id)

        events = db_session.exec(db_session.query(PointsEvent)).all()
        assert len(events) == 0

    def test_award_for_edit_no_editor(self, db_session, test_record):
        """Test no points when editor doesn't exist."""
        fake_editor_id = uuid4()

        award_for_edit(db_session, test_record, fake_editor_id)

        events = db_session.exec(db_session.query(PointsEvent)).all()
        assert len(events) == 0

    def test_award_for_edit_multiple_allowed(
        self, db_session, test_user, test_record
    ):
        """Test that multiple edits can earn points."""
        test_user.streak_multiplier = 1.0
        db_session.add(test_user)
        db_session.commit()

        for _ in range(3):
            award_for_edit(db_session, test_record, test_user.id)

        events = db_session.exec(
            db_session.query(PointsEvent).where(
                PointsEvent.reason == "record_edited"
            )
        ).all()
        assert len(events) == 3

    def test_award_for_edit_with_streak(
        self, db_session, test_user, test_record
    ):
        """Test edit points with active streak."""
        test_user.streak_multiplier = 2.0
        test_user.streak_expires_at = datetime.now(timezone.utc) + timedelta(
            hours=12
        )
        db_session.add(test_user)
        db_session.commit()

        award_for_edit(db_session, test_record, test_user.id)

        db_session.refresh(test_user)
        assert test_user.streak_multiplier == 2.1

    def test_award_for_edit_expired_streak(
        self, db_session, test_user, test_record
    ):
        """Test edit points with expired streak starts new streak."""
        test_user.streak_multiplier = 2.5
        test_user.streak_expires_at = datetime.now(timezone.utc) - timedelta(
            hours=1
        )
        db_session.add(test_user)
        db_session.commit()

        award_for_edit(db_session, test_record, test_user.id)

        db_session.refresh(test_user)
        assert test_user.streak_multiplier == 1.1
        assert test_user.streak_expires_at > datetime.now(timezone.utc)


class TestPointsServiceMocked:
    """Tests for points_service using mocks."""

    def test_award_for_record_mock(self):
        """Test award_for_record with mocked session."""
        mock_session = MagicMock()
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.streak_multiplier = 1.0
        mock_user.streak_expires_at = None

        mock_record = Mock()
        mock_record.uid = uuid4()
        mock_record.user_id = mock_user.id

        mock_session.exec.return_value.first.return_value = None
        mock_session.get.return_value = mock_user

        award_for_record(mock_session, mock_record)

        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    def test_award_for_edit_mock(self):
        """Test award_for_edit with mocked session."""
        mock_session = MagicMock()
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.streak_multiplier = 1.0
        mock_user.streak_expires_at = None

        mock_record = Mock()
        mock_record.uid = uuid4()

        editor_id = mock_user.id

        mock_session.get.return_value = mock_user

        award_for_edit(mock_session, mock_record, editor_id)

        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    def test_award_for_record_with_naive_timezone(self):
        """Test award_for_record handles naive datetime."""
        mock_session = MagicMock()
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.streak_multiplier = 1.5
        mock_user.streak_expires_at = datetime.now() + timedelta(hours=12)

        mock_record = Mock()
        mock_record.uid = uuid4()
        mock_record.user_id = mock_user.id

        mock_session.exec.return_value.first.return_value = None
        mock_session.get.return_value = mock_user

        award_for_record(mock_session, mock_record)

        mock_session.add.assert_called()

    def test_award_for_edit_with_naive_timezone(self):
        """Test award_for_edit handles naive datetime."""
        mock_session = MagicMock()
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.streak_multiplier = 1.5
        mock_user.streak_expires_at = datetime.now() + timedelta(hours=12)

        mock_record = Mock()
        mock_record.uid = uuid4()

        mock_session.get.return_value = mock_user

        award_for_edit(mock_session, mock_record, mock_user.id)

        mock_session.add.assert_called()

    def test_award_for_record_user_not_found(self):
        """Test award_for_record when user not found."""
        mock_session = MagicMock()
        mock_record = Mock()
        mock_record.uid = uuid4()
        mock_record.user_id = uuid4()

        mock_session.exec.return_value.first.return_value = None
        mock_session.get.return_value = None

        award_for_record(mock_session, mock_record)

        mock_session.add.assert_not_called()

    def test_award_for_edit_editor_not_found(self):
        """Test award_for_edit when editor not found."""
        mock_session = MagicMock()
        mock_record = Mock()
        mock_record.uid = uuid4()

        mock_session.get.return_value = None

        award_for_edit(mock_session, mock_record, uuid4())

        mock_session.add.assert_not_called()
