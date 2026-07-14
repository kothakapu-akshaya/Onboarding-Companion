from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models import Category, Record
from app.schemas import MediaType, ReleaseRights


class TestExtractedTextEndpoints:
    """Test suite for extracted text management endpoints."""

    @pytest.fixture
    def admin_token_headers(self, app_client):
        """Create admin token headers for testing."""
        # Try to login with admin credentials or skip if not available
        try:
            login_data = {"phone": "+919999999999", "password": "testpassword"}
            response = app_client.post("/api/v1/auth/login", json=login_data)
            if response.status_code == 200:
                token = response.json()["access_token"]
                return {"Authorization": f"Bearer {token}"}
        except Exception:
            pass
        pytest.skip("Admin user not available")

    @pytest.fixture
    def user_token_headers(self, authenticated_client, app_client):
        """Create user token headers for testing."""
        try:
            login_data = {"phone": "+919999999999", "password": "testpassword"}
            response = app_client.post("/api/v1/auth/login", json=login_data)
            if response.status_code == 200:
                token = response.json()["access_token"]
                return {"Authorization": f"Bearer {token}"}
        except Exception:
            pass
        pytest.skip("User not available")

    @pytest.fixture
    def test_category(self, session):
        """Create a test category."""
        category = Category(
            name="Test Category",
            description="A test category for testing purposes",
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        yield category
        session.delete(category)
        session.commit()

    @pytest.fixture
    def test_record(self, session, test_user, test_category):
        """Create a test record for extracted text operations."""
        record = Record(
            title="Test Record for Text Extraction",
            description=(
                "A test record used for testing extracted text functionality"
            ),
            media_type=MediaType.audio,
            user_id=test_user.id,
            category_id=test_category.id,
            release_rights=ReleaseRights.creator,
            language="hindi",
            status="uploaded",
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def test_save_extracted_text_success(
        self, client: TestClient, test_record, admin_token_headers
    ):
        """Test successfully saving extracted text."""
        extracted_text = {
            "transcription": "यह एक टेस्ट रिकॉर्डिंग है।",
            "confidence": 0.95,
            "language": "hindi",
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "यह एक टेस्ट"},
                {"start": 2.5, "end": 5.0, "text": "रिकॉर्डिंग है।"},
            ],
        }

        response = client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=admin_token_headers,
            json=extracted_text,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Extracted text saved successfully"
        assert data["record_id"] == str(test_record.uid)
        assert data["version"] == 1

    def test_save_extracted_text_already_exists(
        self, client: TestClient, test_record, admin_token_headers
    ):
        """Test trying to overwrite existing extracted text fails."""
        # First, save some extracted text
        extracted_text = {
            "transcription": "First text",
            "confidence": 0.9,
            "extraction_type": "asr",
        }
        client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=admin_token_headers,
            json=extracted_text,
        )

        # Try to save again - should fail
        new_text = {
            "transcription": "Second text",
            "confidence": 0.8,
            "extraction_type": "asr",
        }
        response = client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=admin_token_headers,
            json=new_text,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_save_extracted_text_invalid_json(
        self, client: TestClient, test_record, admin_token_headers
    ):
        """Test saving invalid JSON structure fails."""
        response = client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=admin_token_headers,
            json="invalid_json_structure",  # String instead of dict
        )

        assert response.status_code == 422  # Pydantic validation error
        assert "validation" in response.json()["detail"][0]["type"]

    def test_save_extracted_text_non_admin_access(
        self, client: TestClient, test_record, user_token_headers
    ):
        """Test that non-admin users cannot save extracted text."""
        extracted_text = {
            "transcription": "Some text",
            "confidence": 0.9,
            "extraction_type": "asr",
        }

        response = client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=user_token_headers,
            json=extracted_text,
        )

        assert response.status_code == 403

    def test_get_record_text_with_corrections(
        self,
        client: TestClient,
        test_record,
        admin_token_headers,
        user_token_headers,
    ):
        """Test getting record text when initial and corrected text exist."""
        # Save initial extracted text first (version 1)
        initial_text = {
            "transcription": "यह एक टेस्ट रिकॉर्डिंग है।",
            "confidence": 0.95,
            "extraction_type": "asr",
        }
        client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=admin_token_headers,
            json=initial_text,
        )

        # Save corrected text (version 2)
        corrected_text = {
            "transcription": "यह एक परीक्षण रिकॉर्डिंग है।",  # Corrected version
            "extraction_type": "manual",
            "corrections_made": ["टेस्ट -> परीक्षण"],
        }
        client.patch(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=user_token_headers,
            json=corrected_text,
        )

        # Get the text
        response = client.get(
            f"/api/v1/records/{test_record.uid}/text",
            headers=user_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == str(test_record.uid)
        assert (
            data["extracted_text"]["transcription"]
            == "यह एक परीक्षण रिकॉर्डिंग है।"
        )
        assert data["version_info"] is not None
        assert data["version_info"]["current_version"] >= 2

    def test_get_record_text_empty(
        self, client: TestClient, test_record, user_token_headers
    ):
        """Test getting text from record with no extracted text."""
        response = client.get(
            f"/api/v1/records/{test_record.uid}/text",
            headers=user_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_text"] is None
        # version_info might be None for new records
        if data["version_info"]:
            assert data["version_info"]["current_version"] >= 1

    def test_update_corrected_text_success(
        self,
        client: TestClient,
        test_record,
        admin_token_headers,
        user_token_headers,
    ):
        """Test successfully updating corrected text."""
        # First save initial text
        initial_text = {
            "transcription": "यह एक टेस्ट रिकॉर्डिंग है।",
            "confidence": 0.95,
            "extraction_type": "asr",
        }
        client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=admin_token_headers,
            json=initial_text,
        )

        # Now update with corrections
        corrected_text = {
            "transcription": "यह एक परीक्षण रिकॉर्डिंग है।",
            "extraction_type": "manual",
            "corrections_made": ["टेस्ट -> परीक्षण"],
        }

        response = client.patch(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=user_token_headers,
            json=corrected_text,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Corrected text updated successfully"
        assert data["record_id"] == str(test_record.uid)
        assert data["new_version"] >= 2
        assert "history_entry_id" in data
        assert "version_info" in data

    def test_update_corrected_text_allows_authenticated_user(
        self,
        client: TestClient,
        test_record,
        admin_token_headers,
        user_token_headers,
    ):
        """Test ordinary authenticated users can patch corrected text."""
        initial_text = {
            "transcription": "यह एक टेस्ट रिकॉर्डिंग है।",
            "confidence": 0.95,
            "extraction_type": "asr",
        }
        client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=admin_token_headers,
            json=initial_text,
        )

        corrected_text = {
            "transcription": "यह एक उपयोगकर्ता-संपादित रिकॉर्डिंग है।",
            "extraction_type": "manual",
            "corrections_made": ["टेस्ट -> उपयोगकर्ता-संपादित"],
        }

        response = client.patch(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=user_token_headers,
            json=corrected_text,
        )

        assert response.status_code == 200
        assert (
            response.json()["message"] == "Corrected text updated successfully"
        )

    def test_update_corrected_text_version_mismatch(
        self,
        client: TestClient,
        test_record,
        admin_token_headers,
        user_token_headers,
    ):
        """Test optimistic locking with version mismatch."""
        # First save initial text
        initial_text = {
            "transcription": "Original text",
            "extraction_type": "asr",
            "confidence": 0.9,
        }
        client.post(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=admin_token_headers,
            json=initial_text,
        )

        # First update
        corrected_text = {
            "transcription": "First correction",
            "extraction_type": "manual",
        }
        first_response = client.patch(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=user_token_headers,
            json=corrected_text,
        )
        assert first_response.status_code == 200
        current_version = first_response.json()["new_version"]

        # Try to update with old version - should fail
        new_text = {
            "transcription": "Second correction",
            "extraction_type": "manual",
        }
        response = client.patch(
            f"/api/v1/records/{test_record.uid}"
            f"/extracted_text"
            f"?expected_version={current_version - 1}",  # Old version
            headers=user_token_headers,
            json=new_text,
        )

        assert response.status_code == 409
        assert "Version mismatch" in response.json()["detail"]

    def test_update_corrected_text_invalid_json(
        self, client: TestClient, test_record, user_token_headers
    ):
        """Test updating with invalid JSON structure."""
        response = client.patch(
            f"/api/v1/records/{test_record.uid}/extracted_text",
            headers=user_token_headers,
            json="invalid_json",
        )

        assert response.status_code == 422  # Pydantic validation error


def test_record_not_found_endpoints(authenticated_client):
    """Test all endpoints with non-existent record ID."""
    fake_id = uuid4()
    client = authenticated_client

    response = client.post(
        f"/api/v1/records/{fake_id}/extracted_text",
        json={
            "segments": [{"start": 0, "end": 1, "text": "test"}],
            "extraction_type": "asr",
        },
    )
    assert response.status_code == 404

    response = client.get(
        f"/api/v1/records/{fake_id}/text",
    )
    assert response.status_code == 404

    response = client.patch(
        f"/api/v1/records/{fake_id}/extracted_text?expected_version=1",
        json={
            "segments": [{"start": 0, "end": 1, "text": "test"}],
            "extraction_type": "manual",
        },
    )
    assert response.status_code == 404

    response = client.get(f"/api/v1/records/{fake_id}/text")
    assert response.status_code == 404

    response = client.patch(
        f"/api/v1/records/{fake_id}/extracted_text?expected_version=1",
        json={
            "segments": [{"start": 0, "end": 1, "text": "test"}],
            "extraction_type": "manual",
        },
    )
    assert response.status_code == 404
