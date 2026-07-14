"""Consolidated validation service tests.

Tests service layer orchestration and validation coordination.
"""

import pytest
from pydantic import ValidationError

from app.core.validation_exceptions import (
    ContentValidationError,
    FileValidationError,
    UserValidationError,
    ValidationErrorHandler,
)
from app.schemas.auth_validation import (
    OTPSendValidation,
    OTPValidation,
    PasswordChangeValidation,
    UserLoginValidation,
    UserProfileUpdateValidation,
    UserRegistrationValidation,
)
from app.schemas.upload_validation import (
    MediaType,
)
from app.services.validation_service import (
    AuthValidationService,
    ContentValidationService,
    ValidationOrchestrator,
    validate_content_submission,
    validate_file_upload,
    validate_user_login,
    validate_user_registration,
    validation_orchestrator,
)
from tests.data.test_data import TestData


class TestAuthValidationService:
    """Test authentication validation service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = AuthValidationService()

    def test_validate_user_registration_success(self, user_registration_data):
        """Test successful user registration validation."""
        result = self.service.validate_user_registration(user_registration_data)

        assert isinstance(result, UserRegistrationValidation)
        assert result.phone == "+919876543210"
        assert result.name == "John Doe"
        assert result.email == "john@example.com"

    def test_validate_user_registration_failure(self, invalid_user_data):
        """Test user registration validation failure."""
        with pytest.raises(UserValidationError) as exc_info:
            self.service.validate_user_registration(invalid_user_data)

        assert "User registration validation failed" in str(exc_info.value)

    def test_validate_user_login_success(self, user_login_data):
        """Test successful user login validation."""
        result = self.service.validate_user_login(user_login_data)

        assert isinstance(result, UserLoginValidation)
        assert result.phone == "+919876543210"

    def test_validate_user_login_failure(self):
        """Test user login validation failure."""
        invalid_data = {
            "phone": "5876543210",
            "password": "",
        }

        with pytest.raises(UserValidationError) as exc_info:
            self.service.validate_user_login(invalid_data)

        assert "Login validation failed" in str(exc_info.value)

    def test_validate_otp_request_success(self):
        """Test successful OTP request validation."""
        data = {
            "phone": "9876543210",
            "request_type": "login",
        }
        result = self.service.validate_otp_request(data)

        assert isinstance(result, OTPSendValidation)
        assert result.phone == "+919876543210"

    def test_validate_otp_request_failure(self):
        """Test OTP request validation failure."""
        invalid_data = {
            "phone": "12345",
        }

        with pytest.raises(UserValidationError) as exc_info:
            self.service.validate_otp_request(invalid_data)

        assert "OTP request validation failed" in str(exc_info.value)

    def test_validate_otp_verification_success(self):
        """Test successful OTP verification validation."""
        data = {
            "phone": "9876543210",
            "otp_code": "123456",
            "reference_id": "test_ref",
        }
        result = self.service.validate_otp_verification(data)

        assert isinstance(result, OTPValidation)
        assert result.phone == "+919876543210"
        assert result.otp_code == "123456"

    def test_validate_otp_verification_failure(self):
        """Test OTP verification validation failure."""
        invalid_data = {
            "phone": "invalid",
            "otp_code": "12345",
        }

        with pytest.raises(UserValidationError) as exc_info:
            self.service.validate_otp_verification(invalid_data)

        assert "OTP verification failed" in str(exc_info.value)

    def test_validate_password_change_success(self):
        """Test successful password change validation."""
        data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        }
        result = self.service.validate_password_change(data)

        assert isinstance(result, PasswordChangeValidation)
        assert result.current_password == "OldPass123!"

    def test_validate_password_change_failure(self):
        """Test password change validation failure."""
        invalid_data = {
            "user_id": "test-user-id",
            "current_password": "OldPass123!",
            "new_password": "weak",
            "confirm_new_password": "weak",
        }

        with pytest.raises(UserValidationError) as exc_info:
            self.service.validate_password_change(invalid_data)

        assert "Password change validation failed" in str(exc_info.value)

    def test_validate_password_change_mismatch(self):
        """Test password change with mismatched passwords."""
        invalid_data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
            "confirm_password": "DifferentPass123!",
        }

        with pytest.raises(UserValidationError):
            self.service.validate_password_change(invalid_data)

    def test_validate_profile_update_success(self):
        """Test successful profile update validation."""
        data = {
            "user_id": "test-user-id",
            "name": "Updated Name",
            "email": "updated@example.com",
        }
        result = self.service.validate_profile_update(data)

        assert isinstance(result, UserProfileUpdateValidation)
        assert result.name == "Updated Name"

    def test_validate_profile_update_failure(self):
        """Test profile update validation failure."""
        invalid_data = {
            "user_id": "test-user-id",
            "name": "X",
        }

        with pytest.raises(UserValidationError) as exc_info:
            self.service.validate_profile_update(invalid_data)

        assert "Profile update validation failed" in str(exc_info.value)

    @pytest.mark.parametrize(
        "registration_data",
        [
            TestData.user_registration_data(phone="8876543210"),
            TestData.user_registration_data(email="different@example.com"),
            TestData.user_registration_data(name="Different User"),
            TestData.user_registration_data(gender="female"),
        ],
    )
    def test_registration_variations(self, registration_data):
        """Test registration validation with different valid variations."""
        result = self.service.validate_user_registration(registration_data)
        assert isinstance(result, UserRegistrationValidation)

    @pytest.mark.parametrize(
        "invalid_data",
        [
            TestData.user_registration_data(phone="5876543210"),
            TestData.user_registration_data(password="weak"),
            TestData.user_registration_data(name="A"),
            TestData.user_registration_data(has_given_consent=False),
        ],
    )
    def test_registration_failures(self, invalid_data):
        """Test registration validation failures."""
        with pytest.raises(UserValidationError):
            self.service.validate_user_registration(invalid_data)


class TestContentValidationService:
    """Test content validation service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ContentValidationService()

    def test_validate_content_submission_success(self):
        """Test successful content validation."""
        content_data = TestData.content_data()

        result = self.service.validate_content_submission(
            content_data, media_type=MediaType.audio
        )

        assert result.title == "Sample Audio Recording"
        assert result.description.startswith("This is a valid description")
        assert result.language == "hindi"

    def test_validate_content_submission_failure(self):
        """Test content validation failure."""
        invalid_data = TestData.content_data(
            title="",
            description="Short",
        )

        with pytest.raises(ContentValidationError):
            self.service.validate_content_submission(
                invalid_data, media_type=MediaType.audio
            )

    def test_validate_file_upload_success(self):
        """Test successful file upload validation."""
        file_data = {
            "file_name": "test_audio.wav",
            "file_type": "audio/wav",
            "file_size_bytes": 1024 * 1024,
        }

        result = self.service.validate_file_upload(
            file_data, media_type=MediaType.audio
        )

        assert result.file_name == "test_audio.wav"
        assert result.file_type == "audio/wav"

    def test_validate_file_upload_failure(self):
        """Test file upload validation failure."""
        invalid_file_data = {
            "file_name": "test.exe",
            "file_type": "application/x-executable",
            "file_size_bytes": 10 * 1024 * 1024,
        }

        with pytest.raises(FileValidationError):
            self.service.validate_file_upload(
                invalid_file_data, media_type=MediaType.audio
            )

    def test_validate_content_submission_text(self):
        """Test content submission validation for text media type."""
        text_content = (
            "This is a sample text content with more than fifty characters "
            "to satisfy the validation rules and make the test pass. "
            "This should be long enough."
        )
        content_data = TestData.content_data(
            media_type=MediaType.text,
            text_content=text_content,
        )

        result = self.service.validate_content_submission(
            content_data, media_type=MediaType.text
        )

        assert result.text_content == text_content

    def test_validate_content_submission_video(self):
        """Test content submission validation for video media type."""
        content_data = TestData.content_data(
            media_type=MediaType.video,
            video_file={
                "file_name": "test.mp4",
                "file_type": "video/mp4",
                "file_size_bytes": 5 * 1024 * 1024,
            },
        )
        del content_data["audio_file"]

        result = self.service.validate_content_submission(
            content_data, media_type=MediaType.video
        )

        assert result.video_file.file_name == "test.mp4"

    def test_validate_content_submission_image(self):
        """Test content submission validation for image media type."""
        content_data = TestData.content_data(
            media_type=MediaType.image,
            image_file={
                "file_name": "test.jpg",
                "file_type": "image/jpeg",
                "file_size_bytes": 500 * 1024,
            },
        )
        del content_data["audio_file"]

        result = self.service.validate_content_submission(
            content_data, media_type=MediaType.image
        )

        assert result.image_file.file_name == "test.jpg"

    def test_validate_content_submission_unsupported_type(self):
        """Test content submission with unsupported media type."""
        content_data = TestData.content_data()

        with pytest.raises(ValueError) as exc_info:
            self.service.validate_content_submission(
                content_data, media_type="unsupported"
            )

        assert "Unsupported media type" in str(exc_info.value)

    def test_validate_batch_upload_success(self):
        """Test successful batch upload validation."""
        batch_data = {
            "uploads": [
                {
                    "title": "Item 1",
                    "description": "Description for item 1 that is valid.",
                },
                {
                    "title": "Item 2",
                    "description": "Description for item 2 that is valid.",
                },
            ],
        }

        result = self.service.validate_batch_upload(batch_data)

        assert len(result.uploads) == 2

    def test_validate_batch_upload_failure(self):
        """Test batch upload validation failure."""
        invalid_batch_data = {
            "uploads": [],
        }

        with pytest.raises(ContentValidationError):
            self.service.validate_batch_upload(invalid_batch_data)

    def test_validate_chunked_upload_success(self):
        """Test successful chunked upload validation."""
        chunk_data = {
            "upload_id": "upload-123",
            "chunk_number": 1,
            "total_chunks": 5,
            "chunk_size": 1024 * 1024,
            "total_size": 5 * 1024 * 1024,
        }

        result = self.service.validate_chunked_upload(chunk_data)

        assert result.upload_id == "upload-123"
        assert result.chunk_number == 1
        assert result.total_chunks == 5

    def test_validate_chunked_upload_failure(self):
        """Test chunked upload validation failure."""
        invalid_chunk_data = {
            "upload_id": "upload-123",
            "chunk_number": 0,
            "total_chunks": 5,
            "chunk_size": 1024 * 1024,
            "total_size": 5 * 1024 * 1024,
        }

        with pytest.raises(FileValidationError):
            self.service.validate_chunked_upload(invalid_chunk_data)

    def test_validate_file_extension_consistency_valid(self):
        """Test file extension consistency validation - valid case."""
        result = self.service.validate_file_extension_consistency(
            "video.mp4", "video/mp4"
        )
        assert result is True

    def test_validate_file_extension_consistency_invalid(self):
        """Test file extension consistency validation - invalid case."""
        result = self.service.validate_file_extension_consistency(
            "video.mp4", "video/avi"
        )
        assert result is False

    @pytest.mark.parametrize(
        "content_data",
        [
            TestData.content_data(title="Different Title"),
            TestData.content_data(language="kannada"),
            TestData.content_data(
                media_type=MediaType.text,
                text_content=(
                    "This is a sample text content with more than "
                    "fifty characters to satisfy the validation rules "
                    "and make the test pass. This should be long enough."
                ),
            ),
            TestData.content_data(
                location={"latitude": 19.0760, "longitude": 72.8777}
            ),
        ],
    )
    def test_content_variations(self, content_data):
        """Test content validation with different valid variations."""
        result = self.service.validate_content_submission(
            content_data, media_type=content_data["media_type"]
        )
        assert result.title is not None
        assert result.language is not None

    @pytest.mark.parametrize(
        "invalid_content",
        [
            TestData.content_data(title=""),
            TestData.content_data(title="A"),
            TestData.content_data(description=""),
            TestData.content_data(location={"latitude": 91, "longitude": 77}),
            TestData.content_data(location={"latitude": 12, "longitude": 181}),
        ],
    )
    def test_content_failures(self, invalid_content):
        """Test content validation failures."""
        with pytest.raises(ContentValidationError):
            self.service.validate_content_submission(
                invalid_content, media_type=MediaType.audio
            )


class TestValidationOrchestrator:
    """Test validation orchestrator that coordinates multiple validations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = ValidationOrchestrator()

    def test_validate_user_operation_register(self, user_registration_data):
        """Test validate_user_operation with register."""
        result = self.orchestrator.validate_user_operation(
            "register", user_registration_data
        )
        assert isinstance(result, UserRegistrationValidation)

    def test_validate_user_operation_login(self, user_login_data):
        """Test validate_user_operation with login."""
        result = self.orchestrator.validate_user_operation(
            "login", user_login_data
        )
        assert isinstance(result, UserLoginValidation)

    def test_validate_user_operation_otp_send(self):
        """Test validate_user_operation with otp_send."""
        data = {"phone": "9876543210", "request_type": "login"}
        result = self.orchestrator.validate_user_operation("otp_send", data)
        assert isinstance(result, OTPSendValidation)

    def test_validate_user_operation_otp_verify(self, otp_data):
        """Test validate_user_operation with otp_verify."""
        result = self.orchestrator.validate_user_operation(
            "otp_verify", otp_data
        )
        assert isinstance(result, OTPValidation)

    def test_validate_user_operation_password_change(self):
        """Test validate_user_operation with password_change."""
        data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        }
        result = self.orchestrator.validate_user_operation(
            "password_change", data
        )
        assert isinstance(result, PasswordChangeValidation)

    def test_validate_user_operation_profile_update(self):
        """Test validate_user_operation with profile_update."""
        data = {
            "user_id": "test-id",
            "name": "Updated Name",
        }
        result = self.orchestrator.validate_user_operation(
            "profile_update", data
        )
        assert isinstance(result, UserProfileUpdateValidation)

    def test_validate_user_operation_unknown(self):
        """Test validate_user_operation with unknown operation."""
        with pytest.raises(UserValidationError) as exc_info:
            self.orchestrator.validate_user_operation("unknown", {})

        assert "Unknown user operation" in str(exc_info.value)

    def test_validate_content_operation_content_submit(self):
        """Test validate_content_operation with content_submit."""
        content_data = TestData.content_data()
        result = self.orchestrator.validate_content_operation(
            "content_submit", content_data, MediaType.audio
        )
        assert result.title is not None

    def test_validate_content_operation_file_upload(self):
        """Test validate_content_operation with file_upload."""
        file_data = {
            "file_name": "test.wav",
            "file_type": "audio/wav",
            "file_size_bytes": 1024 * 1024,
        }
        result = self.orchestrator.validate_content_operation(
            "file_upload", file_data, MediaType.audio
        )
        assert result.file_name == "test.wav"

    def test_validate_content_operation_batch_upload(self):
        """Test validate_content_operation with batch_upload."""
        batch_data = {
            "uploads": [
                {"title": "Test", "description": "Test description for batch."}
            ],
        }
        result = self.orchestrator.validate_content_operation(
            "batch_upload", batch_data
        )
        assert len(result.uploads) == 1

    def test_validate_content_operation_chunked_upload(self):
        """Test validate_content_operation with chunked_upload."""
        chunk_data = {
            "upload_id": "upload-123",
            "chunk_number": 1,
            "total_chunks": 3,
            "chunk_size": 1024 * 1024,
            "total_size": 3 * 1024 * 1024,
        }
        result = self.orchestrator.validate_content_operation(
            "chunked_upload", chunk_data
        )
        assert result.upload_id == "upload-123"

    def test_validate_content_operation_content_submit_missing_media_type(self):
        """Test content_submit without media type."""
        with pytest.raises(ContentValidationError) as exc_info:
            self.orchestrator.validate_content_operation("content_submit", {})

        assert "Media type required" in str(exc_info.value)

    def test_validate_content_operation_file_upload_missing_media_type(self):
        """Test file_upload without media type."""
        with pytest.raises(FileValidationError) as exc_info:
            self.orchestrator.validate_content_operation("file_upload", {})

        assert "Media type required" in str(exc_info.value)

    def test_validate_content_operation_unknown(self):
        """Test validate_content_operation with unknown operation."""
        with pytest.raises(ContentValidationError) as exc_info:
            self.orchestrator.validate_content_operation("unknown", {})

        assert "Unknown content operation" in str(exc_info.value)

    def test_complete_submission_validation_success(
        self, user_registration_data
    ):
        """Test complete submission validation success."""
        content_data = TestData.content_data()
        file_data = {
            "file_name": "test_audio.wav",
            "file_type": "audio/wav",
            "file_size_bytes": 1024 * 1024,
        }

        result = self.orchestrator.validate_comprehensive_submission(
            content_data=content_data,
            file_data=file_data,
            media_type=MediaType.audio,
        )

        assert result[0] is not None
        assert result[1] is not None

    def test_complete_submission_validation_without_media_type(self):
        """Test complete submission without media type."""
        with pytest.raises(ContentValidationError) as exc_info:
            self.orchestrator.validate_comprehensive_submission(
                content_data={}, file_data=None, media_type=None
            )

        assert "Media type is required" in str(exc_info.value)

    def test_complete_submission_validation_content_only(self):
        """Test complete submission with content only (no file)."""
        content_data = TestData.content_data()

        result = self.orchestrator.validate_comprehensive_submission(
            content_data=content_data,
            file_data=None,
            media_type=MediaType.audio,
        )

        assert result[0] is not None
        assert result[1] is None

    def test_complete_submission_validation_file_extension_mismatch(self):
        """Test complete submission with mismatched file extension."""
        content_data = TestData.content_data()
        file_data = {
            "file_name": "test.mp4",
            "file_type": "audio/wav",
            "file_size_bytes": 1024 * 1024,
        }

        with pytest.raises(FileValidationError) as exc_info:
            self.orchestrator.validate_comprehensive_submission(
                content_data=content_data,
                file_data=file_data,
                media_type=MediaType.audio,
            )

        assert "File extension does not match file type" in str(exc_info.value)


class TestStandaloneValidationFunctions:
    """Test standalone validation functions."""

    def test_validate_user_registration_function(self, user_registration_data):
        """Test standalone user registration validation function."""
        result = validate_user_registration(user_registration_data)

        assert isinstance(result, UserRegistrationValidation)
        assert result.phone.startswith("+91")

    def test_validate_user_login_function(self, user_login_data):
        """Test standalone user login validation function."""
        result = validate_user_login(user_login_data)

        assert isinstance(result, UserLoginValidation)
        assert result.phone.startswith("+91")

    def test_validate_content_submission_function(self):
        """Test standalone content validation function."""
        content_data = TestData.content_data()

        result = validate_content_submission(
            content_data, media_type=MediaType.audio
        )

        assert result.title is not None
        assert result.language is not None

    def test_validate_file_upload_function(self):
        """Test standalone file upload validation function."""
        file_data = {
            "file_name": "test_audio.wav",
            "file_type": "audio/wav",
            "file_size_bytes": 1024 * 1024,
        }

        result = validate_file_upload(file_data, media_type=MediaType.audio)

        assert result.file_name == "test_audio.wav"

    def test_global_validation_orchestrator_instance(self):
        """Test global validation_orchestrator singleton."""
        assert isinstance(validation_orchestrator, ValidationOrchestrator)
        assert validation_orchestrator.auth_service is not None
        assert validation_orchestrator.content_service is not None


class TestValidationErrorHandler:
    """Test validation error handler integration."""

    def test_format_pydantic_error(self):
        """Test formatting pydantic validation errors."""
        from app.schemas.auth_validation import UserRegistrationValidation

        try:
            UserRegistrationValidation(phone="invalid", name="X", email="bad")
        except ValidationError as e:
            formatted = ValidationErrorHandler.format_pydantic_error(e)
            assert "errors" in formatted
            assert isinstance(formatted["errors"], list)
