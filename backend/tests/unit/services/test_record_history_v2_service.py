"""Tests for record_history_v2_service."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.record_history import (
    ChangeSource,
    ChangeType,
    RecordHistory,
    RecordMajorSnapshot,
    RecordVersion,
)
from app.services.record_history_service import (
    RecordHistoryService,
    _serialize_value,
)


class TestSerializeValueV2:
    """Tests for _serialize_value helper function in V2."""

    def test_serialize_datetime(self):
        """Test datetime serialization."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        result = _serialize_value(dt)
        assert result == "2024-01-15T10:30:00+00:00"

    def test_serialize_string(self):
        """Test string serialization."""
        result = _serialize_value("test string")
        assert result == "test string"

    def test_serialize_none(self):
        """Test None serialization."""
        result = _serialize_value(None)
        assert result is None

    def test_serialize_int(self):
        """Test integer serialization."""
        result = _serialize_value(42)
        assert result == "42"

    def test_serialize_dict(self):
        """Test dict serialization — preserved as-is."""
        result = _serialize_value({"key": "value"})
        assert result == {"key": "value"}

    def test_serialize_list(self):
        """Test list serialization — preserved as-is."""
        result = _serialize_value([1, 2, 3])
        assert result == [1, 2, 3]


class TestRecordHistoryV2Service:
    """Tests for RecordHistoryService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create a RecordHistoryService instance."""
        return RecordHistoryService(mock_session)

    @pytest.fixture
    def mock_record(self):
        """Create a mock record."""
        record = MagicMock()
        record.uid = uuid4()
        record.title = "Test Record"
        record.description = "Test description"
        record.model_dump = MagicMock(
            return_value={
                "uid": str(record.uid),
                "title": "Test Record",
                "description": "Test description",
            }
        )
        return record

    def test_initialize_record_history(
        self, service, mock_session, mock_record
    ):
        """Test initialization of record history."""
        user_id = uuid4()
        mock_session.exec.return_value.first.return_value = None

        history, version = service.initialize_record_history(
            record=mock_record,
            created_by=user_id,
            change_source=ChangeSource.system_process,
        )

        assert history.record_id == mock_record.uid
        assert history.version_number == 0
        assert history.change_type == ChangeType.created
        assert history.change_source == ChangeSource.system_process
        assert history.changed_by == user_id
        assert history.field_changes == {}

        assert version.record_id == mock_record.uid
        assert version.current_version == 0
        assert version.total_changes == 1

        mock_session.add.assert_called()

    def test_create_history_entry(self, service, mock_session, mock_record):
        """Test creating a new history entry."""
        user_id = uuid4()
        version_info = RecordVersion(
            record_id=mock_record.uid,
            current_version=1,
            total_changes=0,
        )
        mock_session.exec.return_value.first.return_value = version_info

        field_changes = {"title": {"old": "Old Title", "new": "New Title"}}

        history = service.create_history_entry(
            record=mock_record,
            changed_by=user_id,
            change_type=ChangeType.updated,
            change_source=ChangeSource.user_edit,
            field_changes=field_changes,
        )

        assert history.record_id == mock_record.uid
        assert history.version_number == 2
        assert history.change_type == ChangeType.updated
        assert history.change_source == ChangeSource.user_edit
        assert history.field_changes == field_changes
        assert history.full_snapshot is None  # not a major version

    def test_calculate_field_changes_no_changes(self, service):
        """Test field change calculation with no changes."""
        old_values = {"title": "Test", "description": "Desc"}
        new_values = {"title": "Test", "description": "Desc"}

        result = service._calculate_field_changes(old_values, new_values)

        assert result == {}

    def test_calculate_field_changes_with_changes(self, service):
        """Test field change calculation with changes."""
        old_values = {"title": "Old Title", "description": "Old Desc"}
        new_values = {"title": "New Title", "description": "Old Desc"}

        result = service._calculate_field_changes(old_values, new_values)

        assert "title" in result
        assert result["title"]["old"] == "Old Title"
        assert result["title"]["new"] == "New Title"

    def test_calculate_field_changes_added_field(self, service):
        """Test field change calculation for added field."""
        old_values = {"title": "Test"}
        new_values = {"title": "Test", "new_field": "New Value"}

        result = service._calculate_field_changes(old_values, new_values)

        assert "new_field" in result
        assert result["new_field"]["old"] is None
        assert result["new_field"]["new"] == "New Value"

    def test_calculate_field_changes_removed_field(self, service):
        """Test field change calculation for removed field."""
        old_values = {"title": "Test", "old_field": "Value"}
        new_values = {"title": "Test"}

        result = service._calculate_field_changes(old_values, new_values)

        assert "old_field" in result
        assert result["old_field"]["old"] == "Value"
        assert result["old_field"]["new"] is None

    def test_capture_record_changes_no_changes(
        self, service, mock_session, mock_record
    ):
        """Test capture record changes when no actual changes."""
        mock_session.exec.return_value.first.return_value = mock_record

        old_values = {"title": "Test", "description": "Desc"}
        new_values = {"title": "Test", "description": "Desc"}

        result = service.capture_record_changes(
            record_id=mock_record.uid,
            old_values=old_values,
            new_values=new_values,
            changed_by=uuid4(),
        )

        assert result is None

    def test_capture_record_changes_with_changes(
        self, service, mock_session, mock_record
    ):
        """Test capture record changes with actual changes."""
        mock_session.exec.return_value.first.return_value = mock_record

        version_info = RecordVersion(
            record_id=mock_record.uid,
            current_version=1,
            total_changes=0,
        )
        mock_session.exec.return_value.first.side_effect = [
            mock_record,
            version_info,
        ]

        old_values = {"title": "Old", "description": "Desc"}
        new_values = {"title": "New", "description": "Desc"}

        result = service.capture_record_changes(
            record_id=mock_record.uid,
            old_values=old_values,
            new_values=new_values,
            changed_by=uuid4(),
        )

        assert result is not None
        assert result.change_type == ChangeType.updated

    def test_get_record_history(self, service, mock_session):
        """Test getting record history."""
        record_id = uuid4()
        mock_history = [
            MagicMock(record_id=record_id, version_number=1),
            MagicMock(record_id=record_id, version_number=0),
        ]
        mock_session.exec.return_value.all.return_value = mock_history

        result = service.get_record_history(record_id, limit=10)

        assert len(result) == 2

    def test_get_record_version(self, service, mock_session):
        """Test getting a specific version."""
        record_id = uuid4()
        version = 1
        mock_history = MagicMock(
            record_id=record_id,
            version_number=version,
            uid=uuid4(),
            change_type="updated",
            change_source="user_edit",
            changed_by=uuid4(),
            full_snapshot={"title": "Old"},
            field_changes={},
            change_reason=None,
            change_metadata=None,
            created_at=datetime.now(timezone.utc),
        )
        mock_session.exec.return_value.first.return_value = mock_history

        result = service.get_record_version(record_id, version)

        assert result is not None
        assert result["record_id"] == record_id
        assert result["version_number"] == version

    def test_compare_versions(self, service, mock_session):
        """Test comparing two versions."""
        record_id = uuid4()
        from_record = MagicMock(
            record_id=record_id,
            version_number=0,
            full_snapshot={"title": "Old"},
        )
        to_record = MagicMock(
            record_id=record_id,
            version_number=1,
            full_snapshot={"title": "New"},
        )
        mock_session.exec.return_value.first.side_effect = [
            from_record,
            to_record,
        ]

        result = service.compare_versions(record_id, 0, 1)

        assert "changed_fields" in result
        assert result["changed_fields"]["title"]["old"] == "Old"
        assert result["changed_fields"]["title"]["new"] == "New"

    def test_get_version_summary_exists(self, service, mock_session):
        """Test getting version summary when exists."""
        record_id = uuid4()
        version_info = RecordVersion(
            record_id=record_id,
            current_version=5,
            total_changes=10,
            last_change_at=datetime.now(timezone.utc),
            user_edits=3,
            admin_edits=2,
            system_updates=5,
        )
        mock_session.exec.return_value.first.return_value = version_info

        result = service.get_version_summary(record_id)

        assert result["current_version"] == 5
        assert result["total_changes"] == 10
        assert result["change_breakdown"]["user_edit"] == 3
        assert result["change_breakdown"]["admin"] == 2
        assert result["change_breakdown"]["system"] == 5

    def test_get_version_summary_not_exists(self, service, mock_session):
        """Test getting version summary when not exists."""
        record_id = uuid4()
        mock_session.exec.return_value.first.return_value = None

        result = service.get_version_summary(record_id)

        assert result["current_version"] == 0
        assert result["total_changes"] == 0

    def test_should_create_major_snapshot(self, service):
        """Test snapshot creation logic."""
        assert (
            service._should_create_major_snapshot(0, ChangeType.created)
            is False
        )
        assert (
            service._should_create_major_snapshot(1, ChangeType.created) is True
        )
        assert (
            service._should_create_major_snapshot(10, ChangeType.updated)
            is True
        )
        assert (
            service._should_create_major_snapshot(5, ChangeType.updated)
            is False
        )
        assert (
            service._should_create_major_snapshot(5, ChangeType.admin_override)
            is True
        )

    def test_calculate_diff(self, service):
        """Test diff calculation."""
        old = {"title": "Old", "description": "Desc"}
        new = {"title": "New", "description": "Desc", "new_field": "Value"}

        result = service._calculate_diff(old, new)

        assert "added" in result
        assert "changed" in result
        assert "removed" in result
        assert result["added"]["new_field"] == "Value"
        assert result["changed"]["title"]["old"] == "Old"
        assert result["changed"]["title"]["new"] == "New"

    def test_get_history_count(self, service, mock_session):
        """Test getting history count."""
        record_id = uuid4()
        mock_session.exec.return_value.first.return_value = 10

        result = service.get_history_count(record_id)

        assert result == 10

    @pytest.mark.skip(
        reason="Complex mock setup required - tested in integration tests"
    )
    def test_get_user_edit_metrics(self, service, mock_session):
        """Test getting user edit metrics."""
        pass


class TestRecordHistoryV2Models:
    """Tests for V2 model structures."""

    def test_record_history_v2_fields(self):
        """Test RecordHistory has required fields."""
        history = RecordHistory(
            record_id=uuid4(),
            version_number=1,
            change_type=ChangeType.updated,
            change_source=ChangeSource.user_edit,
            changed_by=uuid4(),
            field_changes={"title": {"old": "A", "new": "B"}},
            full_snapshot={"title": "B"},
        )

        assert history.field_changes["title"]["old"] == "A"
        assert history.field_changes["title"]["new"] == "B"

    def test_record_version_v2_fields(self):
        """Test RecordVersion has required fields."""
        version = RecordVersion(
            record_id=uuid4(),
            current_version=5,
            total_changes=10,
            user_edits=3,
            admin_edits=2,
            system_updates=5,
        )

        assert version.current_version == 5
        assert version.total_changes == 10
        assert version.user_edits == 3

    def test_record_major_snapshot_fields(self):
        """Test RecordMajorSnapshot has required fields."""
        snapshot = RecordMajorSnapshot(
            record_id=uuid4(),
            version_number=10,
            full_data={"title": "Test"},
            snapshot_type="auto",
        )

        assert snapshot.version_number == 10
        assert snapshot.snapshot_type == "auto"


class TestFieldChangesFormat:
    """Tests for field_changes JSONB format."""

    def test_field_changes_format(self):
        """Test field_changes follows new format."""
        field_changes = {
            "title": {
                "old": "Old Title",
                "new": "New Title",
                "reason": "Correction",
            },
            "description": {
                "old": "Old Desc",
                "new": "New Desc",
                "reason": None,
            },
            "status": {
                "old": None,
                "new": "published",
                "reason": "Status update",
            },
        }

        for field, change in field_changes.items():
            assert "old" in change
            assert "new" in change
            assert "reason" in change


class TestV2FieldChangesToV1:
    """Tests for _v2_field_changes_to_v1 backward-compat transform."""

    def test_updated_field(self):
        """Test updated field conversion."""
        from app.services.record_history_service import _v2_field_changes_to_v1

        v2 = {
            "title": {
                "old": "Old",
                "new": "New",
                "type": "updated",
                "reason": None,
            }
        }
        v1 = _v2_field_changes_to_v1(v2)

        assert v1["title"]["old_value"] == "Old"
        assert v1["title"]["new_value"] == "New"
        assert v1["title"]["change_type"] == "updated"

    def test_added_field(self):
        """Test added field conversion."""
        from app.services.record_history_service import _v2_field_changes_to_v1

        v2 = {
            "title": {
                "old": None,
                "new": "New",
                "type": "added",
                "reason": None,
            }
        }
        v1 = _v2_field_changes_to_v1(v2)

        assert v1["title"]["old_value"] is None
        assert v1["title"]["new_value"] == "New"
        assert v1["title"]["change_type"] == "added"

    def test_removed_field(self):
        """Test removed field conversion."""
        from app.services.record_history_service import _v2_field_changes_to_v1

        v2 = {
            "title": {
                "old": "Old",
                "new": None,
                "type": "removed",
                "reason": None,
            }
        }
        v1 = _v2_field_changes_to_v1(v2)

        assert v1["title"]["old_value"] == "Old"
        assert v1["title"]["new_value"] is None
        assert v1["title"]["change_type"] == "removed"

    def test_field_nulled_inference_uses_stored_type(self):
        """Test that setting a field to null uses stored type, not inference."""
        from app.services.record_history_service import _v2_field_changes_to_v1

        # Stored type is "updated" even though new is None
        v2 = {
            "title": {
                "old": "Old",
                "new": None,
                "type": "updated",
                "reason": "Cleared value",
            }
        }
        v1 = _v2_field_changes_to_v1(v2)

        assert v1["title"]["change_type"] == "updated"
        assert v1["title"]["old_value"] == "Old"
        assert v1["title"]["new_value"] is None

    def test_fallback_inference_removed(self):
        """Test inference when no stored type and old exists, new is None."""
        from app.services.record_history_service import _v2_field_changes_to_v1

        v2 = {"title": {"old": "Old", "new": None, "reason": None}}
        v1 = _v2_field_changes_to_v1(v2)

        assert v1["title"]["change_type"] == "removed"

    def test_fallback_inference_updated(self):
        """Test inference when no stored type and both old and new exist."""
        from app.services.record_history_service import _v2_field_changes_to_v1

        v2 = {"title": {"old": "Old", "new": "New", "reason": None}}
        v1 = _v2_field_changes_to_v1(v2)

        assert v1["title"]["change_type"] == "updated"

    def test_fallback_inference_added(self):
        """Test inference when no stored type and old is None."""
        from app.services.record_history_service import _v2_field_changes_to_v1

        v2 = {"title": {"old": None, "new": "New", "reason": None}}
        v1 = _v2_field_changes_to_v1(v2)

        assert v1["title"]["change_type"] == "added"


class TestV1FieldChangesToV2:
    """Tests for _v1_field_changes_to_v2 transform."""

    def test_conversion_preserves_type(self):
        """Test that V1→V2 conversion preserves the change_type."""
        from app.services.record_history_service import _v1_field_changes_to_v2

        v1 = {
            "title": {
                "old_value": "Old",
                "new_value": "New",
                "change_type": "updated",
            }
        }
        v2 = _v1_field_changes_to_v2(v1)

        assert v2["title"]["old"] == "Old"
        assert v2["title"]["new"] == "New"
        assert v2["title"]["type"] == "updated"


class TestV2EntryToV1Dict:
    """Tests for _v2_entry_to_v1_dict backward-compat transform."""

    def test_converts_record_history_to_v1_shape(self):
        """Test that a RecordHistory ORM object converts to V1-shaped dict."""
        from app.services.record_history_service import _v2_entry_to_v1_dict

        entry = RecordHistory(
            record_id=uuid4(),
            version_number=1,
            change_type=ChangeType.updated,
            change_source=ChangeSource.user_edit,
            changed_by=uuid4(),
            field_changes={
                "title": {"old": "Old", "new": "New", "type": "updated"},
            },
            full_snapshot={"title": "New"},
            change_reason="User edit",
            change_metadata={"source": "web"},
        )

        result = _v2_entry_to_v1_dict(entry)

        assert result["record_snapshot"] == {"title": "New"}
        assert result["field_changes"]["title"]["old_value"] == "Old"
        assert result["field_changes"]["title"]["new_value"] == "New"
        assert result["field_changes"]["title"]["change_type"] == "updated"
        assert result["record_id"] == entry.record_id
        assert result["version_number"] == 1
        assert result["change_metadata"] == {"source": "web"}
