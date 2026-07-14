"""Password reset schemas."""

from pydantic import BaseModel, Field, field_validator

from app.core.validators import validate_password_strength, validate_phone


class PasswordResetInitRequest(BaseModel):
    """Request to initiate password reset process."""

    phone: str = Field(
        ..., description="Phone number with country code (e.g., +919177980938)"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        """Validate phone number format."""
        return validate_phone(v)


class PasswordResetConfirmRequest(BaseModel):
    """Request to confirm password reset with OTP."""

    phone: str = Field(..., description="Phone number with country code")
    otp_code: str = Field(
        ..., min_length=4, max_length=8, description="OTP code received via SMS"
    )
    new_password: str = Field(
        ..., min_length=8, max_length=72, description="New password"
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=72, description="Confirm new password"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        """Validate phone number format."""
        return validate_phone(v)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)

    def model_post_init(self, __context) -> None:
        """Validate that passwords match."""
        if self.new_password != self.confirm_password:
            raise ValueError(
                "New password and confirmation password do not match. "
                "Please ensure both passwords are identical."
            )


class PasswordResetResponse(BaseModel):
    """Response for password reset operations."""

    status: str
    message: str
    reference_id: str | None = None
