"""Tests for validation schema coverage."""

# ruff: noqa: E402

from datetime import date, timedelta

import pydantic as _pydantic
import pytest
from pydantic import ValidationError

_orig_field = _pydantic.Field


def _compat_field(*args, **kwargs):
    kwargs.pop("const", None)
    return _orig_field(*args, **kwargs)


_pydantic.Field = _compat_field

from app.schemas import Gender, MediaType, ReleaseRights
from app.schemas.auth_validation import (
    UserProfileUpdateValidation,
    UserRegistrationValidation,
)
from app.schemas.geo_schemas import Coordinates
from app.schemas.upload_validation import (
    AudioContentValidation,
    AudioFileValidation,
    AudioValidationResult,
    ContentValidationBase,
    ImageContentValidation,
    ImageFileValidation,
    TextContentValidation,
    ValidationErrorDetail,
    ValidationErrorResponse,
    VideoContentValidation,
    VideoFileValidation,
)

UserRegistrationValidation.model_rebuild(_types_namespace={"Gender": Gender})
UserProfileUpdateValidation.model_rebuild(_types_namespace={"Gender": Gender})


VALID_COORDINATES = Coordinates(latitude=17.385, longitude=78.4867)
VALID_DESCRIPTION = (
    "This is a long enough description with varied"
    " words and meaningful context."
)


def _valid_content_base(**overrides):
    data = {
        "title": "Village folklore recording",
        "description": VALID_DESCRIPTION,
        "language": "hindi",
        "release_rights": ReleaseRights.creator,
        "location": VALID_COORDINATES,
    }
    data.update(overrides)
    return data


class TestAudioVideoImageValidation:
    """Test audio, video, and image file validation schemas."""

    def test_audio_validation_result_defaults(self):
        """Test AudioValidationResult default values."""
        result = AudioValidationResult(is_valid=True)
        assert result.errors == []
        assert result.warnings == []

    def test_audio_file_validation_success(self):
        """Test valid audio file validation."""
        model = AudioFileValidation(
            file_name="test.mp3",
            file_type="audio/mpeg",
            file_size_bytes=1024,
            duration_seconds=120,
        )
        assert model.file_type == "audio/mpeg"

    @pytest.mark.parametrize(
        "kwargs, message",
        [
            (
                {
                    "file_name": "test.mp3",
                    "file_type": "audio/xyz",
                    "file_size_bytes": 1024,
                },
                "Unsupported audio format",
            ),
            (
                {
                    "file_name": "test.mp3",
                    "file_type": "audio/mpeg",
                    "file_size_bytes": 512,
                },
                "(?i)too small",
            ),
            (
                {
                    "file_name": "test.mp3",
                    "file_type": "audio/mpeg",
                    "file_size_bytes": 600 * 1024 * 1024,
                },
                "(?i)too large",
            ),
            (
                {
                    "file_name": "test.mp3",
                    "file_type": "audio/mpeg",
                    "file_size_bytes": 1024,
                    "duration_seconds": 4,
                },
                "at least 5 seconds",
            ),
            (
                {
                    "file_name": "test.mp3",
                    "file_type": "audio/mpeg",
                    "file_size_bytes": 1024,
                    "duration_seconds": 1000,
                },
                "must not exceed 15 minutes",
            ),
        ],
    )
    def test_audio_file_validation_errors(self, kwargs, message):
        """Test audio file validation rejects invalid inputs."""
        with pytest.raises(ValidationError, match=message):
            AudioFileValidation(**kwargs)

    def test_video_file_validation_success(self):
        """Test valid video file validation."""
        model = VideoFileValidation(
            file_name="test.mp4",
            file_type="video/mp4",
            file_size_bytes=2048,
            duration_seconds=60,
        )
        assert model.file_type == "video/mp4"

    @pytest.mark.parametrize(
        "kwargs, message",
        [
            (
                {
                    "file_name": "test.mp4",
                    "file_type": "video/xyz",
                    "file_size_bytes": 2048,
                },
                "Unsupported video format",
            ),
            (
                {
                    "file_name": "test.mp4",
                    "file_type": "video/mp4",
                    "file_size_bytes": 512,
                },
                "(?i)too small",
            ),
            (
                {
                    "file_name": "test.mp4",
                    "file_type": "video/mp4",
                    "file_size_bytes": 3 * 1024 * 1024 * 1024,
                },
                "(?i)too large",
            ),
        ],
    )
    def test_video_file_validation_errors(self, kwargs, message):
        """Test video file validation rejects invalid inputs."""
        with pytest.raises(ValidationError, match=message):
            VideoFileValidation(**kwargs)

    def test_image_file_validation_success(self):
        """Test valid image file validation."""
        model = ImageFileValidation(
            file_name="test.png",
            file_type="image/png",
            file_size_bytes=4096,
        )
        assert model.file_type == "image/png"

    @pytest.mark.parametrize(
        "kwargs, message",
        [
            (
                {
                    "file_name": "test.png",
                    "file_type": "image/tiff",
                    "file_size_bytes": 4096,
                },
                "Unsupported image format",
            ),
            (
                {
                    "file_name": "test.png",
                    "file_type": "image/png",
                    "file_size_bytes": 256,
                },
                "(?i)too small",
            ),
            (
                {
                    "file_name": "test.png",
                    "file_type": "image/png",
                    "file_size_bytes": 100 * 1024 * 1024,
                },
                "(?i)too large",
            ),
        ],
    )
    def test_image_file_validation_errors(self, kwargs, message):
        """Test image file validation rejects invalid inputs."""
        with pytest.raises(ValidationError, match=message):
            ImageFileValidation(**kwargs)


class TestContentValidation:
    """Test content validation schemas."""

    def test_content_validation_base_success(self):
        """Test valid content validation base model."""
        model = ContentValidationBase(**_valid_content_base())
        assert model.location.latitude == VALID_COORDINATES.latitude

    @pytest.mark.parametrize(
        "overrides, message",
        [
            ({"title": "   short  "}, "at least 8 characters"),
            ({"title": "AAAAAAAAAAAA"}, "meaningful content"),
            (
                {"title": "THIS TITLE IS DEFINITELY TOO LOUD"},
                "proper capitalization",
            ),
            (
                {"description": "Too short."},
                "at least 16 characters",
            ),
            (
                {"description": "aaaaa aaaaa aaaaa aaaaa aaaaa aaaaa"},
                "meaningful and varied content",
            ),
            (
                {"release_rights": ReleaseRights.NA},
                "Release rights must be declared",
            ),
            (
                {"location": Coordinates(latitude=0.0, longitude=0.0)},
                "appear to be invalid",
            ),
        ],
    )
    def test_content_validation_base_errors(self, overrides, message):
        """Test content validation base rejects invalid inputs."""
        with pytest.raises(ValidationError, match=message):
            ContentValidationBase(**_valid_content_base(**overrides))

    def test_text_content_validation_success(self):
        """Test valid text content validation."""
        model = TextContentValidation(
            **_valid_content_base(),
            text_content=(
                "This is a sufficiently long text payload"
                " with enough distinct words to satisfy"
                " the text content validation logic."
            ),
        )
        assert model.media_type == MediaType.text

    @pytest.mark.parametrize(
        "text_content, message",
        [
            ("short text only", "at least 50 characters"),
            (
                "alpha bravo charlie delta echo foxtrot golf hotel india",
                "at least 10 words",
            ),
            (
                "repeat repeat repeat repeat repeat"
                " repeat repeat repeat repeat repeat",
                "repetitive",
            ),
        ],
    )
    def test_text_content_validation_errors(self, text_content, message):
        """Test text content validation rejects invalid inputs."""
        with pytest.raises(ValidationError, match=message):
            TextContentValidation(
                **_valid_content_base(), text_content=text_content
            )

    def test_audio_content_validation_success(self):
        """Test valid audio content validation."""
        model = AudioContentValidation(
            **_valid_content_base(),
            audio_file=AudioFileValidation(
                file_name="test.wav",
                file_type="audio/wav",
                file_size_bytes=2048,
                duration_seconds=120,
            ),
        )
        assert model.media_type == MediaType.audio

    def test_video_content_validation_success(self):
        """Test valid video content validation."""
        model = VideoContentValidation(
            **_valid_content_base(),
            video_file=VideoFileValidation(
                file_name="test.webm",
                file_type="video/webm",
                file_size_bytes=4096,
                duration_seconds=60,
            ),
        )
        assert model.media_type == MediaType.video

    def test_image_content_validation_success(self):
        """Test valid image content validation."""
        model = ImageContentValidation(
            **_valid_content_base(),
            image_file=ImageFileValidation(
                file_name="test.jpg",
                file_type="image/jpeg",
                file_size_bytes=4096,
            ),
        )
        assert model.media_type == MediaType.image


class TestUserValidation:
    """Test user registration and profile update validation schemas."""

    def test_registration_validation_success(self):
        """Test valid user registration."""
        model = UserRegistrationValidation(
            username="testuser",
            phone="+919876543210",
            name="Test User",
            email="USER@EXAMPLE.COM",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
            gender=Gender.male,
            date_of_birth=date(1990, 1, 1),
            current_place="Hyderabad, Telangana",
            has_given_consent=True,
        )
        assert model.phone == "+919876543210"
        assert model.email == "user@example.com"

    @pytest.mark.parametrize(
        "field_overrides, message",
        [
            ({"phone": "12345678901"}, "Phone number must be 10 digits"),
            ({"phone": "+915123456789"}, "start with a digit greater than 5"),
            ({"name": "!"}, "at least 2 characters"),
            ({"email": "bad-email"}, "valid email address"),
            ({"password": "weakpass"}, "Password is too weak"),
            ({"password": "Weakpass1"}, "Password is too weak"),
            (
                {"date_of_birth": date.today() - timedelta(days=365 * 12)},
                "at least 13 years old",
            ),
            ({"current_place": "   "}, "Place is required"),
            ({"has_given_consent": False}, "agree to the terms"),
            ({"confirm_password": "Mismatch123!"}, "do not match"),
        ],
    )
    def test_registration_validation_errors(self, field_overrides, message):
        """Test user registration rejects invalid inputs."""
        base = {
            "username": "testuser",
            "phone": "+919876543210",
            "name": "Test User",
            "email": "test@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "gender": Gender.male,
            "date_of_birth": date(1990, 1, 1),
            "current_place": "Hyderabad, Telangana",
            "has_given_consent": True,
        }
        base.update(field_overrides)
        with pytest.raises(ValidationError, match=message):
            UserRegistrationValidation(**base)

    def test_profile_update_validation_success(self):
        """Test valid profile update with field trimming."""
        model = UserProfileUpdateValidation(
            name="  Updated User  ",
            email="UPDATED@EXAMPLE.COM",
            current_place="  Hyderabad, Telangana  ",
            date_of_birth=date(1990, 1, 1),
        )
        assert model.name == "Updated User"
        assert model.email == "updated@example.com"


class TestValidationResponseModels:
    """Test validation error response models."""

    def test_validation_error_detail_and_response(self):
        """Test ValidationErrorDetail and ValidationErrorResponse creation."""
        detail = ValidationErrorDetail(
            field="title",
            message="Title is too short",
            invalid_value="abc",
        )
        response = ValidationErrorResponse(
            message="Validation failed",
            errors=[detail],
        )

        assert response.success is False
        assert response.error_type == "validation_error"
        assert response.errors[0].field == "title"
        assert response.timestamp is not None
