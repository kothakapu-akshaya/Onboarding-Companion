"""Validation service layer providing centralized validation logic.

Coordinates between different validation modules and provides high-level
validation functions.
"""

from typing import Any

from pydantic import ValidationError

from app.core.validation_exceptions import (
    ContentValidationError,
    FileValidationError,
    UserValidationError,
)
from app.schemas import MediaType
from app.schemas.auth_validation import (
    OTPSendValidation,
    OTPValidation,
    PasswordChangeValidation,
    UserLoginValidation,
    UserProfileUpdateValidation,
    UserRegistrationValidation,
)
from app.schemas.upload_validation import (
    AudioContentValidation,
    AudioFileValidation,
    BatchUploadValidation,
    ChunkedUploadValidation,
    ImageContentValidation,
    ImageFileValidation,
    TextContentValidation,
    TextFileValidation,
    VideoContentValidation,
    VideoFileValidation,
    get_file_validator_by_type,
    validate_file_extension_match,
)


class AuthValidationService:
    """Service for authentication-related validations."""

    @staticmethod
    def validate_user_registration(
        data: dict[str, Any],
    ) -> UserRegistrationValidation:
        """Validate user registration data.

        Args:
            data: User registration data

        Returns:
            UserRegistrationValidation: Validated user data

        Raises:
            UserValidationError: If validation fails
        """
        try:
            return UserRegistrationValidation(**data)
        except ValidationError as e:
            raise UserValidationError(
                message="User registration validation failed",
                field="registration",
                error_code="REGISTRATION_INVALID",
            ) from e

    @staticmethod
    def validate_user_login(data: dict[str, Any]) -> UserLoginValidation:
        """Validate user login data.

        Args:
            data: User login data

        Returns:
            UserLoginValidation: Validated login data

        Raises:
            UserValidationError: If validation fails
        """
        try:
            return UserLoginValidation(**data)
        except ValidationError as e:
            raise UserValidationError(
                message="Login validation failed",
                field="login",
                error_code="LOGIN_INVALID",
            ) from e

    @staticmethod
    def validate_otp_request(data: dict[str, Any]) -> OTPSendValidation:
        """Validate OTP send request.

        Args:
            data: OTP request data

        Returns:
            OTPSendValidation: Validated OTP request

        Raises:
            UserValidationError: If validation fails
        """
        try:
            return OTPSendValidation(**data)
        except ValidationError as e:
            raise UserValidationError(
                message="OTP request validation failed",
                field="otp_request",
                error_code="OTP_REQUEST_INVALID",
            ) from e

    @staticmethod
    def validate_otp_verification(data: dict[str, Any]) -> OTPValidation:
        """Validate OTP verification data.

        Args:
            data: OTP verification data

        Returns:
            OTPValidation: Validated OTP data

        Raises:
            UserValidationError: If validation fails
        """
        try:
            return OTPValidation(**data)
        except ValidationError as e:
            raise UserValidationError(
                message="OTP verification failed",
                field="otp_verification",
                error_code="OTP_INVALID",
            ) from e

    @staticmethod
    def validate_password_change(
        data: dict[str, Any],
    ) -> PasswordChangeValidation:
        """Validate password change data.

        Args:
            data: Password change data

        Returns:
            PasswordChangeValidation: Validated password change data

        Raises:
            UserValidationError: If validation fails
        """
        try:
            return PasswordChangeValidation(**data)
        except ValidationError as e:
            raise UserValidationError(
                message="Password change validation failed",
                field="password_change",
                error_code="PASSWORD_CHANGE_INVALID",
            ) from e

    @staticmethod
    def validate_profile_update(
        data: dict[str, Any],
    ) -> UserProfileUpdateValidation:
        """Validate user profile update data.

        Args:
            data: Profile update data

        Returns:
            UserProfileUpdateValidation: Validated profile data

        Raises:
            UserValidationError: If validation fails
        """
        try:
            return UserProfileUpdateValidation(**data)
        except ValidationError as e:
            raise UserValidationError(
                message="Profile update validation failed",
                field="profile_update",
                error_code="PROFILE_UPDATE_INVALID",
            ) from e


class ContentValidationService:
    """Service for content and upload validations."""

    @staticmethod
    def validate_content_submission(
        data: dict[str, Any], media_type: MediaType
    ) -> (
        TextContentValidation
        | AudioContentValidation
        | VideoContentValidation
        | ImageContentValidation
    ):
        """Validate content submission based on media type.

        Args:
            data: Content submission data
            media_type: Type of media being submitted

        Returns:
            Appropriate content validation object

        Raises:
            ContentValidationError: If validation fails
        """
        try:
            if media_type == MediaType.text:
                return TextContentValidation(**data)
            elif media_type == MediaType.audio:
                return AudioContentValidation(**data)
            elif media_type == MediaType.video:
                return VideoContentValidation(**data)
            elif media_type == MediaType.image:
                return ImageContentValidation(**data)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

        except ValidationError as e:
            raise ContentValidationError(
                message=(
                    f"Content validation failed for {media_type} submission"
                ),
                field="content",
                error_code=f"{media_type.upper()}_CONTENT_INVALID",
            ) from e

    @staticmethod
    def validate_file_upload(
        file_data: dict[str, Any], media_type: MediaType
    ) -> (
        AudioFileValidation
        | VideoFileValidation
        | ImageFileValidation
        | TextFileValidation
    ):
        """Validate file upload based on media type.

        Args:
            file_data: File upload data
            media_type: Type of media file

        Returns:
            Appropriate file validation object

        Raises:
            FileValidationError: If validation fails
        """
        try:
            validator_class = get_file_validator_by_type(media_type)
            return validator_class(**file_data)

        except ValidationError as e:
            raise FileValidationError(
                message=f"File validation failed for {media_type} upload",
                field="file",
                error_code=f"{media_type.upper()}_FILE_INVALID",
            ) from e

    @staticmethod
    def validate_batch_upload(data: dict[str, Any]) -> BatchUploadValidation:
        """Validate batch upload request.

        Args:
            data: Batch upload data

        Returns:
            BatchUploadValidation: Validated batch data

        Raises:
            ContentValidationError: If validation fails
        """
        try:
            return BatchUploadValidation(**data)
        except ValidationError as e:
            raise ContentValidationError(
                message="Batch upload validation failed",
                field="batch_upload",
                error_code="BATCH_UPLOAD_INVALID",
            ) from e

    @staticmethod
    def validate_chunked_upload(
        data: dict[str, Any],
    ) -> ChunkedUploadValidation:
        """Validate chunked upload request.

        Args:
            data: Chunked upload data

        Returns:
            ChunkedUploadValidation: Validated chunk data

        Raises:
            FileValidationError: If validation fails
        """
        try:
            return ChunkedUploadValidation(**data)
        except ValidationError as e:
            raise FileValidationError(
                message="Chunked upload validation failed",
                field="chunked_upload",
                error_code="CHUNKED_UPLOAD_INVALID",
            ) from e

    @staticmethod
    def validate_file_extension_consistency(
        filename: str, mime_type: str
    ) -> bool:
        """Validate that file extension matches MIME type.

        Args:
            filename: Name of the file
            mime_type: MIME type of the file

        Returns:
            bool: True if consistent, False otherwise
        """
        return validate_file_extension_match(filename, mime_type)


class ValidationOrchestrator:
    """Main orchestrator for all validation services.

    Provides high-level validation interface for the application.
    """

    def __init__(self):
        """Initialize the CompositeValidationService."""
        self.auth_service = AuthValidationService()
        self.content_service = ContentValidationService()

    def validate_user_operation(
        self, operation: str, data: dict[str, Any]
    ) -> Any:
        """Validate user-related operations.

        Args:
            operation: Type of user operation
            data: Operation data

        Returns:
            Validated data object

        Raises:
            UserValidationError: If validation fails
        """
        operation_map = {
            "register": self.auth_service.validate_user_registration,
            "login": self.auth_service.validate_user_login,
            "otp_send": self.auth_service.validate_otp_request,
            "otp_verify": self.auth_service.validate_otp_verification,
            "password_change": self.auth_service.validate_password_change,
            "profile_update": self.auth_service.validate_profile_update,
        }

        validator = operation_map.get(operation)
        if not validator:
            raise UserValidationError(
                message=f"Unknown user operation: {operation}",
                field="operation",
                error_code="UNKNOWN_OPERATION",
            )

        return validator(data)

    def validate_content_operation(
        self,
        operation: str,
        data: dict[str, Any],
        media_type: MediaType | None = None,
    ) -> Any:
        """Validate content-related operations.

        Args:
            operation: Type of content operation
            data: Operation data
            media_type: Media type for content operations

        Returns:
            Validated data object

        Raises:
            ContentValidationError, FileValidationError: If validation fails
        """
        if operation == "content_submit":
            if not media_type:
                raise ContentValidationError(
                    message="Media type required for content submission",
                    field="media_type",
                    error_code="MEDIA_TYPE_MISSING",
                )
            return self.content_service.validate_content_submission(
                data, media_type
            )

        elif operation == "file_upload":
            if not media_type:
                raise FileValidationError(
                    message="Media type required for file upload",
                    field="media_type",
                    error_code="MEDIA_TYPE_MISSING",
                )
            return self.content_service.validate_file_upload(data, media_type)

        elif operation == "batch_upload":
            return self.content_service.validate_batch_upload(data)

        elif operation == "chunked_upload":
            return self.content_service.validate_chunked_upload(data)

        else:
            raise ContentValidationError(
                message=f"Unknown content operation: {operation}",
                field="operation",
                error_code="UNKNOWN_OPERATION",
            )

    def validate_comprehensive_submission(
        self,
        content_data: dict[str, Any],
        file_data: dict[str, Any] | None = None,
        media_type: MediaType | None = None,
    ) -> tuple:
        """Validate complete content submission with file.

        Args:
            content_data: Content metadata
            file_data: File information (if applicable)
            media_type: Type of media

        Returns:
            tuple: (validated_content, validated_file)

        Raises:
            ContentValidationError, FileValidationError: If validation fails
        """
        if not media_type:
            raise ContentValidationError(
                message="Media type is required for comprehensive validation",
                field="media_type",
                error_code="MEDIA_TYPE_MISSING",
            )

        # Validate content
        validated_content = self.validate_content_operation(
            "content_submit", content_data, media_type
        )

        # Validate file if provided
        validated_file = None
        if file_data:
            validated_file = self.validate_content_operation(
                "file_upload", file_data, media_type
            )

            # Cross-validate file extension consistency
            if "file_name" in file_data and "file_type" in file_data:
                if not self.content_service.validate_file_extension_consistency(
                    file_data["file_name"], file_data["file_type"]
                ):
                    raise FileValidationError(
                        message="File extension does not match file type",
                        field="file_consistency",
                        error_code="FILE_EXTENSION_MISMATCH",
                    )

        return validated_content, validated_file


# Global validation orchestrator instance
validation_orchestrator = ValidationOrchestrator()


# Convenience functions for common validations
def validate_user_registration(
    data: dict[str, Any],
) -> UserRegistrationValidation:
    """Validate user registration data."""
    return validation_orchestrator.validate_user_operation("register", data)


def validate_user_login(data: dict[str, Any]) -> UserLoginValidation:
    """Validate user login data."""
    return validation_orchestrator.validate_user_operation("login", data)


def validate_content_submission(data: dict[str, Any], media_type: MediaType):
    """Validate content submission."""
    return validation_orchestrator.validate_content_operation(
        "content_submit", data, media_type
    )


def validate_file_upload(data: dict[str, Any], media_type: MediaType):
    """Validate file upload."""
    return validation_orchestrator.validate_content_operation(
        "file_upload", data, media_type
    )
