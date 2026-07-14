"""OTP authentication schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validators import validate_phone
from app.schemas import RoleRead
from app.schemas.auth_validation import UserSignupStep1Validation


class OTPLoginSendRequest(BaseModel):
    """OTP login send request schema."""

    phone: str = Field(
        ..., description="Phone number with country code (e.g., +919177980938)"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        return validate_phone(v)


class OTPResponse(BaseModel):
    """OTP response schema."""

    status: str
    message: str
    reference_id: str | None = None


class OTPLoginVerifyRequest(BaseModel):
    """OTP login verify request schema."""

    phone: str = Field(..., description="Phone number with country code")
    otp_code: str = Field(
        ..., min_length=4, max_length=8, description="OTP code"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        return validate_phone(v)


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str | None = None
    phone: str
    roles: list[RoleRead] = []


class OTPSignupSendRequest(BaseModel):
    """OTP signup send request schema."""

    phone: str = Field(
        ..., description="Phone number with country code (e.g., +919177980938)"
    )
    email: EmailStr = Field(..., description="Email address")
    is_intern: bool = Field(default=False)

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        return validate_phone(v)


class OTPSignupResendRequest(BaseModel):
    """OTP signup resend request schema."""

    phone: str = Field(
        ..., description="Phone number with country code (e.g., +919177980938)"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        return validate_phone(v)


class OTPSignupVerifyRequest(UserSignupStep1Validation):
    """OTP signup verify request schema."""

    otp_code: str = Field(
        ..., min_length=4, max_length=8, description="OTP code"
    )
