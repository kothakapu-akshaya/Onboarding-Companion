import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class OTPBase(SQLModel):
    """Base OTP model."""

    phone: str = Field(
        index=True, description="Phone number (with country code)"
    )
    otp_hash: str = Field(description="Hashed OTP code")
    attempts: int = Field(
        default=0, description="Number of verification attempts"
    )
    is_verified: bool = Field(
        default=False, description="Whether OTP was successfully verified"
    )
    expires_at: datetime = Field(description="OTP expiry timestamp")
    reference_id: str | None = Field(
        default=None, description="SMS service reference ID"
    )


class OTP(OTPBase, table=True):
    """OTP model."""

    __tablename__ = "otp"  # type: ignore[bad-override]

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class OTPCreate(OTPBase):
    """OTP creation schema."""

    pass


class OTPRead(OTPBase):
    """OTP read schema."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
