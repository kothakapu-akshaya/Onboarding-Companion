import pytest
from fastapi.testclient import TestClient

from app.models import Record
from app.schemas import MediaType, ReleaseRights


@pytest.fixture
def ocr_test_record(session, test_user, test_category):
    record = Record(
        title="OCR Validation Record",
        description="Record for OCR segment validation",
        media_type=MediaType.document,
        user_id=test_user.id,
        category_id=test_category.id,
        release_rights=ReleaseRights.creator,
        language="telugu",
        status="uploaded",
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def test_save_ocr_extracted_text_requires_layout_fields(
    client: TestClient, ocr_test_record, admin_token_headers
):
    payload = {
        "transcription": "OCR text",
        "extraction_type": "ocr",
        "segments": [{"start": 0, "end": 1, "text": "Paragraph 1"}],
    }
    response = client.post(
        f"/api/v1/records/{ocr_test_record.uid}/extracted_text",
        headers=admin_token_headers,
        json=payload,
    )
    assert response.status_code == 422
    assert "missing required fields" in response.text


def test_save_ocr_extracted_text_with_ordered_segments_succeeds(
    client: TestClient, ocr_test_record, admin_token_headers
):
    payload = {
        "transcription": "OCR text",
        "extraction_type": "ocr",
        "segments": [
            {
                "start": 0,
                "end": 1,
                "text": "Paragraph 1",
                "bbox": [76, 51, 367, 952],
                "type": "text",
                "reading_order": 1,
            },
            {
                "start": 0,
                "end": 1,
                "text": "Paragraph 2",
                "bbox": [393, 237, 657, 430],
                "type": "text",
                "reading_order": 2,
            },
        ],
    }
    response = client.post(
        f"/api/v1/records/{ocr_test_record.uid}/extracted_text",
        headers=admin_token_headers,
        json=payload,
    )
    assert response.status_code == 200
