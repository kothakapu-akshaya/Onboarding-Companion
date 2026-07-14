"""Tests for record-related response schemas."""

import uuid

from app.schemas import ContributionResponse
from app.schemas.upload_validation import RecordUpdateValidation


class TestContributionResponseInvalidAudio:
    """Tests for speech_not_detected in ContributionResponse."""

    def test_defaults_to_false(self):
        """speech_not_detected defaults to False when not provided."""
        schema = ContributionResponse(
            id=uuid.uuid4(),
            size=1024,
            reviewed=False,
            title="Test",
        )
        assert schema.speech_not_detected is False

    def test_accepts_true(self):
        """speech_not_detected=True is accepted."""
        schema = ContributionResponse(
            id=uuid.uuid4(),
            size=1024,
            reviewed=False,
            title="Test",
            speech_not_detected=True,
        )
        assert schema.speech_not_detected is True

    def test_accepts_false_explicit(self):
        """speech_not_detected=False is accepted explicitly."""
        schema = ContributionResponse(
            id=uuid.uuid4(),
            size=1024,
            reviewed=False,
            title="Test",
            speech_not_detected=False,
        )
        assert schema.speech_not_detected is False


class TestRecordUpdateValidationInvalidAudio:
    """Tests for speech_not_detected in RecordUpdateValidation."""

    def test_accepts_true(self):
        schema = RecordUpdateValidation(speech_not_detected=True)
        assert schema.speech_not_detected is True

    def test_accepts_false(self):
        schema = RecordUpdateValidation(speech_not_detected=False)
        assert schema.speech_not_detected is False

    def test_defaults_to_none(self):
        schema = RecordUpdateValidation()
        assert schema.speech_not_detected is None
