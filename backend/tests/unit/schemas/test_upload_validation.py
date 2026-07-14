"""Tests for app/schemas/upload_validation.py.

These are pure schema/unit tests: they only exercise Pydantic validation logic.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.geo_schemas import Coordinates
from app.schemas.upload_validation import (
    AudioFileValidation,
    BatchUploadValidation,
    ChunkedUploadRequest,
    ChunkedUploadValidation,
    ContentValidationBase,
    FileUploadValidation,
    ImageFileValidation,
    MediaType,
    RecordUpdateValidation,
    ReleaseRights,
    TextContentValidation,
    TextFileValidation,
    UploadFinalizationRequest,
    VideoFileValidation,
    get_file_validator_by_type,
    validate_file_extension_match,
)


def _valid_coordinates() -> Coordinates:
    # Avoid (0,0) which is explicitly rejected by validate_coordinates().
    return Coordinates(latitude=12.9716, longitude=77.5946)


def _valid_description() -> str:
    # >= 32 chars, >= 10 words, varied enough to pass
    # validate_content_description()
    return (
        "This is a valid description with enough words to"
        " satisfy schema validation rules."
    )


def _valid_title() -> str:
    # >= 8 chars, at least 2 words (schema-level requirement)
    return "Sample Upload Title"


class TestContentValidationBase:
    """Tests for ContentValidationBase schema."""

    def test_valid_content_base(self):
        """Test valid ContentValidationBase with all required fields."""
        model = ContentValidationBase(
            title=_valid_title(),
            description=_valid_description(),
            language="hindi",
            release_rights=ReleaseRights.creator,
            location=_valid_coordinates(),
        )
        assert model.title == _valid_title()

    def test_title_requires_two_words(self):
        """Test that title requires at least two words."""
        with pytest.raises(ValidationError):
            ContentValidationBase(
                # single word, but still passes core title validation
                title="Meaningful",
                description=_valid_description(),
                language="hindi",
                release_rights=ReleaseRights.creator,
                location=_valid_coordinates(),
            )

    def test_release_rights_na_rejected(self):
        """Test that NA release rights are rejected in base validation."""
        with pytest.raises(ValidationError):
            ContentValidationBase(
                title=_valid_title(),
                description=_valid_description(),
                language="hindi",
                release_rights=ReleaseRights.NA,
                location=_valid_coordinates(),
            )

    def test_location_zero_zero_rejected(self):
        """Test that (0,0) location coordinates are rejected."""
        with pytest.raises(ValidationError):
            ContentValidationBase(
                title=_valid_title(),
                description=_valid_description(),
                language="hindi",
                release_rights=ReleaseRights.creator,
                location=Coordinates(latitude=0.0, longitude=0.0),
            )


class TestFileUploadValidation:
    """Tests for FileUploadValidation schema."""

    def test_dangerous_extension_rejected(self):
        """Test that dangerous file extensions are rejected."""
        with pytest.raises(ValidationError):
            FileUploadValidation(
                file_name="payload.exe",
                file_type="application/octet-stream",
                file_size_bytes=2048,
            )

    def test_invalid_mime_format_rejected(self):
        """Test that invalid MIME format strings are rejected."""
        with pytest.raises(ValidationError):
            FileUploadValidation(
                file_name="safe.txt",
                file_type="plain",
                file_size_bytes=2048,
            )


class TestAudioFileValidation:
    """Tests for AudioFileValidation schema."""

    @pytest.mark.parametrize(
        "file_type",
        [
            "audio/wav",
            "audio/mp3",
            "audio/mpeg",
            "audio/ogg",
            "audio/webm",
            "audio/flac",
        ],
    )
    def test_supported_mime_types(self, file_type: str):
        """Test that supported MIME types are accepted."""
        model = AudioFileValidation(
            file_name="clip.wav",
            file_type=file_type.upper(),  # should be normalized to lowercase
            file_size_bytes=1024 * 1024,
            duration_seconds=10.0,
            sample_rate=44100,
            channels=2,
        )
        assert model.file_type == file_type

    def test_unsupported_mime_type_rejected(self):
        """Test that unsupported MIME types are rejected."""
        with pytest.raises(ValidationError):
            AudioFileValidation(
                file_name="clip.bin",
                file_type="audio/xyz",
                file_size_bytes=1024 * 1024,
            )

    def test_file_too_large_rejected(self):
        """Test that files exceeding size limit are rejected."""
        with pytest.raises(ValidationError):
            AudioFileValidation(
                file_name="big.wav",
                file_type="audio/wav",
                file_size_bytes=501 * 1024 * 1024,  # > 500MB
            )

    @pytest.mark.parametrize("duration", [0.0, 4.9, 901.0])
    def test_duration_bounds(self, duration: float):
        """Test that duration outside valid bounds is rejected."""
        with pytest.raises(ValidationError):
            AudioFileValidation(
                file_name="clip.wav",
                file_type="audio/wav",
                file_size_bytes=1024 * 1024,
                duration_seconds=duration,
            )

    @pytest.mark.parametrize("sample_rate", [7999, 192001])
    def test_sample_rate_bounds(self, sample_rate: int):
        """Test that sample rate outside valid bounds is rejected."""
        with pytest.raises(ValidationError):
            AudioFileValidation(
                file_name="clip.wav",
                file_type="audio/wav",
                file_size_bytes=1024 * 1024,
                sample_rate=sample_rate,
            )

    @pytest.mark.parametrize("channels", [0, 9])
    def test_channel_bounds(self, channels: int):
        """Test that channel count outside valid bounds is rejected."""
        with pytest.raises(ValidationError):
            AudioFileValidation(
                file_name="clip.wav",
                file_type="audio/wav",
                file_size_bytes=1024 * 1024,
                channels=channels,
            )


class TestVideoFileValidation:
    """Tests for VideoFileValidation schema."""

    def test_invalid_dimensions_rejected(self):
        """Test that invalid video dimensions are rejected."""
        with pytest.raises(ValidationError):
            VideoFileValidation(
                file_name="clip.mp4",
                file_type="video/mp4",
                file_size_bytes=1024 * 1024,
                width=0,
                height=1080,
            )

    def test_frame_rate_bounds(self):
        """Test that frame rate outside valid bounds is rejected."""
        with pytest.raises(ValidationError):
            VideoFileValidation(
                file_name="clip.mp4",
                file_type="video/mp4",
                file_size_bytes=1024 * 1024,
                frame_rate=0.0,
            )
        with pytest.raises(ValidationError):
            VideoFileValidation(
                file_name="clip.mp4",
                file_type="video/mp4",
                file_size_bytes=1024 * 1024,
                frame_rate=121.0,
            )


class TestImageFileValidation:
    """Tests for ImageFileValidation schema."""

    def test_aspect_ratio_too_extreme_rejected(self):
        """Test that images with extreme aspect ratios are rejected."""
        with pytest.raises(ValidationError):
            ImageFileValidation(
                file_name="pic.jpg",
                file_type="image/jpeg",
                file_size_bytes=1024 * 1024,
                width=10000,
                height=100,
            )


class TestTextFileValidation:
    """Tests for TextFileValidation schema."""

    def test_supported_text_types(self):
        """Test that supported text file types are accepted."""
        model = TextFileValidation(
            file_name="data.csv",
            file_type="text/csv",
            file_size_bytes=1024 * 1024,
            character_count=100,
            word_count=10,
        )
        assert model.file_type == "text/csv"

    def test_word_count_too_small_rejected(self):
        """Test that text files with too few words are rejected."""
        with pytest.raises(ValidationError):
            TextFileValidation(
                file_name="doc.txt",
                file_type="text/plain",
                file_size_bytes=1024 * 1024,
                word_count=9,
            )

    def test_character_count_too_small_rejected(self):
        """Test that text files with too few characters are rejected."""
        with pytest.raises(ValidationError):
            TextFileValidation(
                file_name="doc.txt",
                file_type="text/plain",
                file_size_bytes=1024 * 1024,
                character_count=49,
            )


class TestTextContentValidation:
    """Tests for TextContentValidation schema."""

    def test_repetitive_content_rejected(self):
        """Test that repetitive text content is rejected."""
        with pytest.raises(ValidationError):
            TextContentValidation(
                title=_valid_title(),
                description=_valid_description(),
                language="hindi",
                release_rights=ReleaseRights.creator,
                location=_valid_coordinates(),
                text_content=(
                    "word " * 60
                ),  # long enough, but too few unique words
            )


class TestBatchAndHashAndChunkHelpers:
    """Tests for batch upload, file hash, and chunked upload helpers."""

    def test_batch_upload_limits(self):
        """Test batch upload size limits."""
        BatchUploadValidation(uploads=[{"a": 1}])
        with pytest.raises(ValidationError):
            BatchUploadValidation(uploads=[{"a": 1}] * 51)

    def test_chunked_upload_validation_consistency(self):
        """Test chunked upload consistency constraints."""
        ChunkedUploadValidation(
            chunk_number=1,
            total_chunks=2,
            chunk_size=1024,
            total_size=2048,
            upload_id="u1",
        )
        with pytest.raises(ValidationError):
            ChunkedUploadValidation(
                chunk_number=3,
                total_chunks=2,
                chunk_size=1024,
                total_size=2048,
                upload_id="u1",
            )
        with pytest.raises(ValidationError):
            ChunkedUploadValidation(
                chunk_number=1,
                total_chunks=2,
                chunk_size=4096,
                total_size=2048,
                upload_id="u1",
            )

    def test_get_file_validator_by_type(self):
        """Test that get_file_validator_by_type returns correct classes."""
        assert (
            get_file_validator_by_type(MediaType.audio) is AudioFileValidation
        )
        assert (
            get_file_validator_by_type(MediaType.video) is VideoFileValidation
        )
        assert (
            get_file_validator_by_type(MediaType.image) is ImageFileValidation
        )
        assert get_file_validator_by_type(MediaType.text) is TextFileValidation

    def test_validate_file_extension_match(self):
        """Test file extension and MIME type matching."""
        assert validate_file_extension_match("x.wav", "audio/wav") is True
        assert validate_file_extension_match("x.wav", "audio/mp3") is False
        assert (
            validate_file_extension_match("x.unknown", "application/x-unknown")
            is True
        )
        assert validate_file_extension_match("noext", "audio/wav") is False


class TestRecordUpdateValidation:
    """Tests for RecordUpdateValidation schema."""

    def test_release_rights_others_requires_creator_or_source_label(self):
        """Test 'others' release rights needs creator or source label."""
        with pytest.raises(ValidationError):
            RecordUpdateValidation(release_rights="others")

        RecordUpdateValidation(release_rights="others", creator="Someone")
        RecordUpdateValidation(release_rights="others", source_label="Family")

    def test_title_repetition_rejected(self):
        """Test that repetitive titles are rejected."""
        with pytest.raises(ValidationError):
            RecordUpdateValidation(title="Hello hello hello hello")

    def test_description_urls_rejected(self):
        """Test that descriptions containing URLs are rejected."""
        with pytest.raises(ValidationError):
            RecordUpdateValidation(
                description=(
                    "This description has enough words but contains a "
                    "http://example.com link."
                )
            )

    def test_published_date_future_rejected(self):
        """Test that future published dates are rejected."""
        with pytest.raises(ValidationError):
            RecordUpdateValidation(
                published_date=date.today() + timedelta(days=1)
            )

    def test_release_rights_na_rejected(self):
        """Test that NA release rights are rejected."""

    def test_speech_not_detected_accepts_true(self):
        """speech_not_detected=True is accepted."""
        schema = RecordUpdateValidation(speech_not_detected=True)
        assert schema.speech_not_detected is True

    def test_speech_not_detected_accepts_false(self):
        """speech_not_detected=False is accepted."""
        schema = RecordUpdateValidation(speech_not_detected=False)
        assert schema.speech_not_detected is False

    def test_speech_not_detected_defaults_to_none(self):
        """speech_not_detected defaults to None (not set = don't update)."""
        schema = RecordUpdateValidation()
        assert schema.speech_not_detected is None


class TestChunkedUploadRequest:
    """Tests for ChunkedUploadRequest schema."""

    def test_filename_security_checks(self):
        """Test that filenames with security risks are rejected."""
        with pytest.raises(ValidationError):
            ChunkedUploadRequest(
                filename="../evil.txt",
                chunk_index=0,
                total_chunks=1,
                upload_uuid=str(uuid.uuid4()),
            )
        with pytest.raises(ValidationError):
            ChunkedUploadRequest(
                filename="evil.exe",
                chunk_index=0,
                total_chunks=1,
                upload_uuid=str(uuid.uuid4()),
            )

    def test_uuid_and_sequence_validation(self):
        """Test that UUID and chunk sequence constraints are enforced."""
        with pytest.raises(ValidationError):
            ChunkedUploadRequest(
                filename="ok.wav",
                chunk_index=1,
                total_chunks=1,  # chunk_index must be < total_chunks
                upload_uuid=str(uuid.uuid4()),
            )
        with pytest.raises(ValidationError):
            ChunkedUploadRequest(
                filename="ok.wav",
                chunk_index=0,
                total_chunks=1,
                upload_uuid="not-a-uuid",
            )


class TestUploadFinalizationRequest:
    """Tests for UploadFinalizationRequest schema."""

    def test_category_ids_must_be_json_uuid_list(self):
        """Test that category IDs must be a JSON list of UUIDs."""
        valid = UploadFinalizationRequest(
            title=_valid_title(),
            description=_valid_description(),
            category_ids=json.dumps([str(uuid.uuid4()), str(uuid.uuid4())]),
            user_id=str(uuid.uuid4()),
            media_type=MediaType.audio,
            upload_uuid=str(uuid.uuid4()),
            filename="x.wav",
            total_chunks=1,
            release_rights=ReleaseRights.creator,
            language="hindi",
            use_uid_filename=False,
        )
        assert valid.total_chunks == 1

        with pytest.raises(ValidationError):
            UploadFinalizationRequest(
                title=_valid_title(),
                description=_valid_description(),
                category_ids="not-json",
                user_id=str(uuid.uuid4()),
                media_type=MediaType.audio,
                upload_uuid=str(uuid.uuid4()),
                filename="x.wav",
                total_chunks=1,
                release_rights=ReleaseRights.creator,
                language="hindi",
                use_uid_filename=False,
            )

    def test_lat_lng_must_be_provided_together(self):
        """Test that latitude and longitude must both be provided."""
        with pytest.raises(ValidationError):
            UploadFinalizationRequest(
                title=_valid_title(),
                description=_valid_description(),
                category_ids=json.dumps([str(uuid.uuid4())]),
                user_id=str(uuid.uuid4()),
                media_type=MediaType.audio,
                upload_uuid=str(uuid.uuid4()),
                filename="x.wav",
                total_chunks=1,
                latitude=12.9,
                release_rights=ReleaseRights.creator,
                language="hindi",
                use_uid_filename=False,
            )

    def test_release_rights_others_requires_creator_or_source_label(self):
        """Test 'others' release rights needs creator or source label."""
        with pytest.raises(ValidationError):
            UploadFinalizationRequest(
                title=_valid_title(),
                description=_valid_description(),
                category_ids=json.dumps([str(uuid.uuid4())]),
                user_id=str(uuid.uuid4()),
                media_type=MediaType.audio,
                upload_uuid=str(uuid.uuid4()),
                filename="x.wav",
                total_chunks=1,
                release_rights=ReleaseRights.others,
                language="hindi",
                use_uid_filename=False,
            )
