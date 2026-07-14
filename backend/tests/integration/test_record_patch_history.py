"""Integration tests for record PATCH endpoint history tracking."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import col, select

from app.models.category import Category
from app.models.record import MediaType, Record, ReleaseRights
from app.models.record_history import ChangeSource, RecordHistory, RecordVersion
from app.models.user import User
from app.schemas import Gender


class TestRecordPatchHistory:
    """Test history tracking in record PATCH operations."""

    def setup_test_data(self, db_session):
        """Setup test user, category, and record."""
        # Create test user
        user = User(
            phone="1234567890",
            name="Test User",
            email="test@example.com",
            gender=Gender.male,
            date_of_birth="1990-01-01",
            place="Test City",
            hashed_password="hashed_password",
            is_active=True,
            has_given_consent=True,
        )
        db_session.add(user)

        # Create test category
        category = Category(
            name="test-category",
            title="Test Category",
            description="Test category for testing",
            published=True,
            rank=1,
        )
        db_session.add(category)
        db_session.flush()

        # Create test record
        record = Record(
            title="Original Title",
            description=(
                "Original description that is long enough"
                " to meet minimum requirements for testing"
                " purposes"
            ),
            media_type=MediaType.text,
            language="english",
            user_id=user.id,
            category_id=category.id,
            release_rights=ReleaseRights.creator,
            creator="Test User",
        )
        db_session.add(record)
        db_session.commit()

        return user, category, record

    def test_patch_record_creates_history_entry(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test that PATCH request creates history entry."""
        user, category, record = self.setup_test_data(db_session)

        # Update the record via PATCH
        update_data = {"title": "Updated Title", "language": "hindi"}

        response = client.patch(
            f"/api/v1/records/{record.uid}",
            json=update_data,
            headers=auth_headers(user.id),
        )

        assert response.status_code == 200

        # Check that history entry was created
        history_entries = db_session.exec(
            select(RecordHistory).where(RecordHistory.record_id == record.uid)
        ).all()

        assert len(history_entries) == 1
        history = history_entries[0]

        assert history.change_source == ChangeSource.user_edit
        assert history.changed_by == user.id
        assert history.version_number == 1
        assert history.change_reason == "User edit via PATCH endpoint"

        # Check field changes
        field_changes = history.field_changes
        assert "title" in field_changes
        assert field_changes["title"]["old_value"] == "Original Title"
        assert field_changes["title"]["new_value"] == "Updated Title"

        assert "language" in field_changes
        assert field_changes["language"]["old_value"] == "english"
        assert field_changes["language"]["new_value"] == "hindi"

        # Check record snapshot
        snapshot = history.record_snapshot
        assert snapshot["title"] == "Updated Title"
        assert snapshot["language"] == "hindi"

    def test_multiple_patches_increment_versions(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test that multiple PATCH requests increment version numbers."""
        user, category, record = self.setup_test_data(db_session)

        # First update
        response1 = client.patch(
            f"/api/v1/records/{record.uid}",
            json={"title": "First Update"},
            headers=auth_headers(user.id),
        )
        assert response1.status_code == 200

        # Second update
        response2 = client.patch(
            f"/api/v1/records/{record.uid}",
            json={
                "description": (
                    "Updated description that is long"
                    " enough to meet minimum requirements"
                ),
            },
            headers=auth_headers(user.id),
        )
        assert response2.status_code == 200

        # Check version numbers
        history_entries = db_session.exec(
            select(RecordHistory)
            .where(RecordHistory.record_id == record.uid)
            .order_by(col(RecordHistory.version_number))
        ).all()

        assert len(history_entries) == 2
        assert history_entries[0].version_number == 1
        assert history_entries[1].version_number == 2

        # Check version tracking
        version_info = db_session.exec(
            select(RecordVersion).where(RecordVersion.record_id == record.uid)
        ).first()

        assert version_info is not None
        assert version_info.current_version == 2
        assert version_info.total_changes == 2
        assert version_info.user_edit_changes == 2

    def test_no_actual_changes_no_history(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test that PATCH with no actual changes doesn't create history."""
        user, category, record = self.setup_test_data(db_session)

        # "Update" with same values
        update_data = {
            "title": "Original Title",  # Same as original
            "language": "english",  # Same as original
        }

        response = client.patch(
            f"/api/v1/records/{record.uid}",
            json=update_data,
            headers=auth_headers(user.id),
        )

        assert response.status_code == 200

        # Should not create history entry since no actual changes
        history_entries = db_session.exec(
            select(RecordHistory).where(RecordHistory.record_id == record.uid)
        ).all()

        assert len(history_entries) == 0

    def test_location_change_tracking(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test that location changes are properly tracked."""
        user, category, record = self.setup_test_data(db_session)

        # Update location
        update_data = {"location": {"latitude": 40.7128, "longitude": -74.0060}}

        response = client.patch(
            f"/api/v1/records/{record.uid}",
            json=update_data,
            headers=auth_headers(user.id),
        )

        assert response.status_code == 200

        # Check history entry
        history = db_session.exec(
            select(RecordHistory).where(RecordHistory.record_id == record.uid)
        ).first()

        assert history is not None

        # Check location in snapshot
        snapshot = history.record_snapshot
        assert "location" in snapshot
        assert snapshot["location"]["latitude"] == 40.7128
        assert snapshot["location"]["longitude"] == -74.0060

        # Check field changes
        field_changes = history.field_changes
        assert "location" in field_changes
        assert (
            field_changes["location"]["old_value"] is None
            or field_changes["location"]["old_value"] == "None"
        )
        # New value should contain the location data
        assert "40.7128" in str(field_changes["location"]["new_value"])

    def test_complex_update_with_multiple_fields(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test complex update with multiple field changes."""
        user, category, record = self.setup_test_data(db_session)

        # Complex update
        update_data = {
            "title": "Completely New Title",
            "description": (
                "Completely new description that meets"
                " the minimum length requirements for"
                " testing purposes"
            ),
            "language": "bengali",
            "release_rights": "others",
            "creator": "Different Creator",
        }

        response = client.patch(
            f"/api/v1/records/{record.uid}",
            json=update_data,
            headers=auth_headers(user.id),
        )

        assert response.status_code == 200

        # Check history entry
        history = db_session.exec(
            select(RecordHistory).where(RecordHistory.record_id == record.uid)
        ).first()

        assert history is not None
        field_changes = history.field_changes

        # Verify all changes were captured
        expected_changes = [
            "title",
            "description",
            "language",
            "release_rights",
            "creator",
        ]
        for field in expected_changes:
            assert field in field_changes, (
                f"Field '{field}' not found in changes"
            )

        # Verify specific change values
        assert field_changes["title"]["old_value"] == "Original Title"
        assert field_changes["title"]["new_value"] == "Completely New Title"

        assert field_changes["language"]["old_value"] == "english"
        assert field_changes["language"]["new_value"] == "bengali"

        assert field_changes["release_rights"]["old_value"] == "creator"
        assert field_changes["release_rights"]["new_value"] == "others"

    def test_any_user_can_edit_with_history(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test that any authenticated user can edit any record.

        History captures the editor.
        """
        user, category, record = self.setup_test_data(db_session)

        # Create another user
        other_user = User(
            phone="9876543210",
            name="Other User",
            email="other@example.com",
            gender=Gender.female,
            date_of_birth="1995-01-01",
            place="Other City",
            hashed_password="other_password",
            is_active=True,
            has_given_consent=True,
        )
        db_session.add(other_user)
        db_session.commit()

        # Different user can successfully update the record
        response = client.patch(
            f"/api/v1/records/{record.uid}",
            json={"title": "Updated by Different User"},
            headers=auth_headers(other_user.id),
        )

        assert response.status_code == 200

        # Should create history entry with the actual editor's details
        history_entries = db_session.exec(
            select(RecordHistory).where(RecordHistory.record_id == record.uid)
        ).all()

        assert len(history_entries) == 1
        history = history_entries[0]

        # Verify the history captures the actual editor
        # (other_user), not the original owner
        assert history.changed_by == other_user.id
        assert history.change_source == ChangeSource.user_edit

        # Verify the change was applied
        updated_record = db_session.get(Record, record.uid)
        assert updated_record.title == "Updated by Different User"

    def test_patch_record_not_found_no_history(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test that PATCH to non-existent record doesn't create history."""
        user, category, record = self.setup_test_data(db_session)

        # Try to update non-existent record
        fake_id = uuid4()
        response = client.patch(
            f"/api/v1/records/{fake_id}",
            json={"title": "Non-existent"},
            headers=auth_headers(user.id),
        )

        assert response.status_code == 404

        # Should not create any history entries
        history_entries = db_session.exec(
            select(RecordHistory).where(RecordHistory.record_id == fake_id)
        ).all()

        assert len(history_entries) == 0

    def test_patch_validation_error_no_history(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test that PATCH with validation errors doesn't create history."""
        user, category, record = self.setup_test_data(db_session)

        # Invalid update data (title too short)
        response = client.patch(
            f"/api/v1/records/{record.uid}",
            json={"title": ""},  # Empty title should fail validation
            headers=auth_headers(user.id),
        )

        assert response.status_code == 422

        # Should not create history entry due to validation failure
        history_entries = db_session.exec(
            select(RecordHistory).where(RecordHistory.record_id == record.uid)
        ).all()

        assert len(history_entries) == 0

    def test_history_captures_user_attribution(
        self, client: TestClient, db_session, auth_headers
    ):
        """Test that history properly captures user attribution."""
        user, category, record = self.setup_test_data(db_session)

        response = client.patch(
            f"/api/v1/records/{record.uid}",
            json={"title": "Updated by specific user"},
            headers=auth_headers(user.id),
        )

        assert response.status_code == 200

        # Check user attribution in history
        history = db_session.exec(
            select(RecordHistory).where(RecordHistory.record_id == record.uid)
        ).first()

        assert history is not None
        assert history.changed_by == user.id
        assert history.change_source == ChangeSource.user_edit

        # Check version info also tracks user
        version_info = db_session.exec(
            select(RecordVersion).where(RecordVersion.record_id == record.uid)
        ).first()

        assert version_info is not None
        assert version_info.last_changed_by == user.id
