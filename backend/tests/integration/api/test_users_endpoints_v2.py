"""Integration tests for user endpoints."""

from uuid import uuid4

from app.models import Record
from app.models.record_history import ChangeSource, ChangeType, RecordHistory


class TestGetUsers:
    """Tests for GET /users endpoint."""

    def test_get_users_as_admin(
        self, client, db_session, test_admin, admin_headers
    ):
        """Test getting users as admin."""
        response = client.get("/api/v1/users/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_users_forbidden(
        self, client, db_session, test_user, auth_headers
    ):
        """Test getting users as non-admin."""
        response = client.get("/api/v1/users/", headers=auth_headers)

        assert response.status_code == 403

    def test_get_users_no_auth(self, client, db_session):
        """Test getting users without authentication."""
        response = client.get("/api/v1/users/")

        assert response.status_code == 403


class TestSearchUsers:
    """Tests for GET /users/search endpoint."""

    def test_search_users_success(
        self, client, db_session, test_user, auth_headers
    ):
        """Test searching users."""
        response = client.get(
            "/api/v1/users/search?query=test", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_users_no_auth(self, client, db_session):
        """Test searching users without authentication."""
        response = client.get("/api/v1/users/search?query=test")

        assert response.status_code == 403


class TestGetUser:
    """Tests for GET /users/{identifier} endpoint."""

    def test_get_user_by_id(self, client, db_session, test_user, auth_headers):
        """Test getting user by ID."""
        response = client.get(
            f"/api/v1/users/{test_user.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == test_user.phone

    def test_get_user_by_username(
        self, client, db_session, test_user, auth_headers
    ):
        """Test getting user by username."""
        response = client.get(
            f"/api/v1/users/{test_user.username}", headers=auth_headers
        )

        assert response.status_code == 200

    def test_get_user_not_found(
        self, client, db_session, test_user, auth_headers
    ):
        """Test getting non-existent user."""
        response = client.get(f"/api/v1/users/{uuid4()}", headers=auth_headers)

        assert response.status_code == 404


class TestUpdateUser:
    """Tests for PUT /users/{identifier} endpoint."""

    def test_update_own_profile(
        self, client, db_session, test_user, auth_headers
    ):
        """Test updating own profile."""
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_update_another_user_forbidden(
        self,
        client,
        db_session,
        test_user,
        auth_headers,
        test_admin,
        admin_headers,
    ):
        """Test updating another user's profile."""
        response = client.put(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers,
            json={"name": "Updated Name"},
        )

        assert response.status_code == 403

    def test_update_user_not_found(
        self, client, db_session, test_user, auth_headers
    ):
        """Test updating non-existent user."""
        response = client.put(
            f"/api/v1/users/{uuid4()}",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404


class TestUserRoles:
    """Tests for user role management endpoints."""

    def test_get_user_roles(self, client, db_session, test_user, admin_headers):
        """Test getting user roles."""
        response = client.get(
            f"/api/v1/users/{test_user.id}/roles", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_assign_roles_to_user(
        self, client, db_session, test_user, test_admin, admin_headers
    ):
        """Test assigning roles to user."""
        response = client.post(
            f"/api/v1/users/{test_user.id}/roles",
            headers=admin_headers,
            json=[2],  # reviewer role
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_add_role_to_user(
        self, client, db_session, test_user, test_admin, admin_headers
    ):
        """Test adding a single role to user."""
        response = client.put(
            f"/api/v1/users/{test_user.id}/roles/add?role_id=2",
            headers=admin_headers,
        )

        assert response.status_code == 200

    def test_remove_role_from_user(
        self, client, db_session, test_user, test_admin, admin_headers
    ):
        """Test removing a role from user."""
        response = client.delete(
            f"/api/v1/users/{test_user.id}/roles/2", headers=admin_headers
        )

        assert response.status_code == 200


class TestUserContributions:
    """Tests for user contributions endpoints."""

    def test_get_user_contributions(
        self, client, db_session, test_user, test_record, auth_headers
    ):
        """Test getting user contributions."""
        response = client.get(
            f"/api/v1/users/{test_user.id}/contributions", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_contributions" in data
        assert "contributions_by_media_type" in data
        assert "audio_contributions" in data
        assert "video_contributions" in data
        assert "text_contributions" in data
        assert "image_contributions" in data
        assert "document_contributions" in data
        assert "compute_audio_count" in data
        assert "edit_audio_count" in data
        assert "review_audio_count" in data
        assert "document_pages" in data

    def test_get_user_contributions_returns_history_based_edit_and_review_counts(  # noqa: E501
        self, authenticated_client, db_session, test_user
    ):
        edited_record = Record(
            title="Edited audio record",
            description="Record used for edit contribution stats",
            media_type="audio",
            user_id=test_user.id,
            release_rights="creator",
            language="hindi",
            status="uploaded",
            duration_seconds=75,
        )
        reviewed_document = Record(
            title="Reviewed document record",
            description="Document used for extracted-text review stats",
            media_type="document",
            user_id=test_user.id,
            release_rights="creator",
            language="hindi",
            status="uploaded",
            page_count=6,
        )
        ignored_text = Record(
            title="Initial extracted text record",
            description=(
                "Should not count as review because old extracted text is null"
            ),
            media_type="text",
            user_id=test_user.id,
            release_rights="creator",
            language="hindi",
            status="uploaded",
        )
        db_session.add(edited_record)
        db_session.add(reviewed_document)
        db_session.add(ignored_text)
        db_session.commit()
        db_session.refresh(edited_record)
        db_session.refresh(reviewed_document)
        db_session.refresh(ignored_text)

        db_session.add(
            RecordHistory(
                record_id=edited_record.uid,
                version_number=1,
                change_type=ChangeType.updated,
                change_source=ChangeSource.user_edit,
                changed_by=test_user.id,
                record_snapshot={},
                field_changes={
                    "title": {"old_value": "Old", "new_value": "New"}
                },
                change_reason="Metadata edit",
            )
        )
        db_session.add(
            RecordHistory(
                record_id=reviewed_document.uid,
                version_number=1,
                change_type=ChangeType.updated,
                change_source=ChangeSource.user_edit,
                changed_by=test_user.id,
                record_snapshot={},
                field_changes={
                    "extracted_text": {
                        "old_value": {"segments": [{"text": "before"}]},
                        "new_value": {"segments": [{"text": "after"}]},
                    }
                },
                change_reason="Extracted text edit",
            )
        )
        db_session.add(
            RecordHistory(
                record_id=ignored_text.uid,
                version_number=1,
                change_type=ChangeType.updated,
                change_source=ChangeSource.ai_processing,
                changed_by=test_user.id,
                record_snapshot={},
                field_changes={
                    "extracted_text": {
                        "old_value": None,
                        "new_value": {"segments": [{"text": "fresh"}]},
                    }
                },
                change_reason="Initial extracted text creation",
            )
        )
        db_session.commit()

        response = authenticated_client.get(
            f"/api/v1/users/{test_user.id}/contributions"
        )

        assert response.status_code == 200
        data = response.json()
        assert "audio_contributions" in data
        assert data["edit_audio_count"] >= 1
        assert data["compute_document_count"] >= 1
        assert data["compute_text_count"] >= 1
        assert data["review_audio_count"] == 0
        assert data["review_document_count"] >= 1
        assert data["review_text_count"] == 0

    def test_get_user_contributions_by_media_type(
        self, client, db_session, test_user, test_record, auth_headers
    ):
        """Test getting contributions by media type."""
        response = client.get(
            f"/api/v1/users/{test_user.id}/contributions/text",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "contributions" in data


class TestUserPasswordChange:
    """Tests for user password change endpoint."""

    def test_change_own_password(
        self, client, db_session, test_user, auth_headers
    ):
        """Test changing own password."""
        response = client.put(
            f"/api/v1/users/{test_user.id}/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!",
            },
        )

        assert response.status_code == 200

    def test_change_password_mismatch(
        self, client, db_session, test_user, auth_headers
    ):
        """Test password change with mismatch."""
        response = client.put(
            f"/api/v1/users/{test_user.id}/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword",
                "new_password": "NewPass123!",
                "confirm_password": "DifferentPass123!",
            },
        )

        assert response.status_code == 400

    def test_change_password_wrong_current(
        self, client, db_session, test_user, auth_headers
    ):
        """Test password change with wrong current password."""
        response = client.put(
            f"/api/v1/users/{test_user.id}/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!",
            },
        )

        assert response.status_code == 400


class TestUserFollow:
    """Tests for user follow/unfollow endpoints."""

    def test_follow_user(
        self, client, db_session, test_user, test_admin, auth_headers
    ):
        """Test following a user."""
        response = client.post(
            f"/api/v1/users/{test_admin.id}/follow", headers=auth_headers
        )

        assert response.status_code == 200

    def test_cannot_follow_self(
        self, client, db_session, test_user, auth_headers
    ):
        """Test cannot follow yourself."""
        response = client.post(
            f"/api/v1/users/{test_user.id}/follow", headers=auth_headers
        )

        assert response.status_code == 400

    def test_unfollow_user(
        self, client, db_session, test_user, test_admin, auth_headers
    ):
        """Test unfollowing a user."""
        # First follow
        client.post(
            f"/api/v1/users/{test_admin.id}/follow", headers=auth_headers
        )

        # Then unfollow
        response = client.delete(
            f"/api/v1/users/{test_admin.id}/follow", headers=auth_headers
        )

        assert response.status_code == 200

    def test_get_followers(
        self, client, db_session, test_user, test_admin, auth_headers
    ):
        """Test getting followers."""
        response = client.get(
            f"/api/v1/users/{test_user.id}/followers", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "followers" in data

    def test_get_following(
        self, client, db_session, test_user, test_admin, auth_headers
    ):
        """Test getting following."""
        response = client.get(
            f"/api/v1/users/{test_user.id}/following", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "following" in data


class TestUserProfile:
    """Tests for user profile endpoint."""

    def test_get_user_profile(
        self, client, db_session, test_user, auth_headers
    ):
        """Test getting user profile."""
        response = client.get(
            f"/api/v1/users/{test_user.id}/profile", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data

    def test_get_user_profile_with_streaks(
        self, client, db_session, test_user, auth_headers
    ):
        """Test getting user profile with streaks."""
        response = client.get(
            f"/api/v1/users/{test_user.id}/profile?include=streaks",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_get_user_profile_with_summary(
        self, client, db_session, test_user, auth_headers
    ):
        """Test getting user profile with summary."""
        response = client.get(
            f"/api/v1/users/{test_user.id}/profile?include=summary",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "average_edits_per_record" in data["summary"]["edits"]
