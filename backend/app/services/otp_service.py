"""OTP service for authentication."""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from sqlmodel import Session, desc, select

from app.core.config import settings
from app.models.otp import OTP

logger = logging.getLogger(__name__)


class OTPService:
    """Service for OTP generation, verification, and SMS delivery."""

    def __init__(self, db: Session):
        """Initialize OTPService with a database session."""
        self.db = db
        self.expiry_minutes = settings.OTP_EXPIRY_MINUTES
        self.max_attempts = settings.OTP_MAX_ATTEMPTS
        self.rate_limit_minutes = settings.OTP_RATE_LIMIT_MINUTES

    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP code."""
        return "".join([str(secrets.randbelow(10)) for _ in range(length)])

    def hash_otp(self, otp: str, phone: str) -> str:
        """Hash OTP with phone number as salt for security."""
        salt = f"{phone}{settings.SECRET_KEY}"
        return hmac.new(salt.encode(), otp.encode(), hashlib.sha256).hexdigest()

    def verify_otp_hash(self, otp: str, phone: str, stored_hash: str) -> bool:
        """Verify OTP against stored hash."""
        computed_hash = self.hash_otp(otp, phone)
        return hmac.compare_digest(computed_hash, stored_hash)

    async def send_otp_sms(self, phone: str, otp: str) -> str | None:
        """Send OTP via SMS using the configured SMS service."""
        try:
            clean_phone = phone.replace("+91", "")
            sms_text = settings.OTP_SMS_TEXT.format(otp=otp)

            payload = {
                "route": "dlt_manual",
                "sender_id": settings.OTP_SENDER_ID,
                "template_id": settings.OTP_TEMPLATE_ID,
                "message": sms_text,
                "entity_id": settings.OTP_ENTITY_ID,
                "numbers": clean_phone,
            }
            headers = {
                "authorization": settings.OTP_API_KEY,
                "Content-Type": "application/json",
            }

            logger.info(
                f"Sending OTP SMS to {phone} via {settings.OTP_SERVICE_URL}"
            )
            logger.info(f"Debug: {clean_phone}")

            response = requests.post(
                settings.OTP_SERVICE_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                # Ozonetel typically returns text response, not JSON
                result_text = response.text.strip()
                logger.info(f"SMS API response: {result_text}")

                # Check if response indicates success
                if (
                    "success" in result_text.lower() or len(result_text) > 5
                ):  # Assuming successful response has content
                    logger.info(
                        f"SMS sent successfully. Response: {result_text}"
                    )
                    return result_text  # Return the response as reference ID
                else:
                    logger.error(f"SMS service error: {result_text}")
                    return None
            else:
                logger.error(
                    f"SMS service HTTP error: {response.status_code} - "
                    f"{response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return None

    async def check_rate_limit(self, phone: str) -> bool:
        """Check if OTP can be sent (rate limiting)."""
        result = await self.check_rate_limit_detailed(phone)
        return result["allowed"]

    async def check_rate_limit_detailed(self, phone: str) -> dict[str, Any]:
        """Check rate limit with detailed information."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=self.rate_limit_minutes
        )

        statement = (
            select(OTP)
            .where(OTP.phone == phone, OTP.created_at > cutoff_time)
            .order_by(desc(OTP.created_at))
        )
        recent_otp = self.db.exec(statement).first()

        if recent_otp is None:
            return {"allowed": True, "wait_minutes": 0}

        # Calculate time remaining
        next_allowed_time = recent_otp.created_at + timedelta(
            minutes=self.rate_limit_minutes
        )
        wait_time = next_allowed_time - datetime.now(timezone.utc)
        wait_minutes = max(
            0, int(wait_time.total_seconds() / 60) + 1
        )  # Round up

        return {
            "allowed": False,
            "wait_minutes": wait_minutes,
            "next_allowed_at": next_allowed_time,
        }

    def get_valid_otp(self, phone: str) -> OTP | None:
        """Get valid (non-expired, non-verified) OTP for phone number."""
        now = datetime.now(timezone.utc)

        logger.info(f"Fetching valid OTP for {phone} at {now}")

        statement = (
            select(OTP)
            .where(
                OTP.phone == phone,
                not OTP.is_verified,
                OTP.attempts < self.max_attempts,
            )
            .order_by(desc(OTP.created_at))
        )
        otp = self.db.exec(statement).first()

        if otp:
            # If expires_at is naive, make it aware
            if otp.expires_at.tzinfo is None:
                expires_at = otp.expires_at.replace(tzinfo=timezone.utc)
                logger.info(
                    f"Converted naive expires_at to aware: {expires_at}"
                )
            else:
                expires_at = otp.expires_at
            if expires_at > now:
                return otp

        return None

    async def send_otp(self, phone: str) -> dict[str, Any]:
        """Send OTP to phone number."""
        # Check rate limiting with detailed info
        rate_limit_result = await self.check_rate_limit_detailed(phone)
        if not rate_limit_result["allowed"]:
            wait_minutes = rate_limit_result["wait_minutes"]
            return {
                "status": "error",
                "message": (
                    f"Please wait {wait_minutes} minute(s) before "
                    "requesting another OTP"
                ),
            }

        return await self._send_otp_internal(phone)

    async def send_signup_otp(self, phone: str) -> dict[str, Any]:
        """Send OTP for signup (no registration required)."""
        # Check rate limiting with detailed info
        rate_limit_result = await self.check_rate_limit_detailed(phone)
        if not rate_limit_result["allowed"]:
            wait_minutes = rate_limit_result["wait_minutes"]
            return {
                "status": "error",
                "message": (
                    f"Please wait {wait_minutes} minute(s) before "
                    "requesting another OTP"
                ),
            }

        return await self._send_otp_internal(phone)

    async def _send_otp_internal(self, phone: str) -> dict[str, Any]:
        """Internal method to send OTP."""
        # Generate OTP
        otp_code = self.generate_otp()
        print(f"Generated OTP for {phone}: {otp_code}")  # Remove in production

        # Send SMS
        reference_id = await self.send_otp_sms(phone, otp_code)
        if not reference_id:
            return {
                "status": "error",
                "message": "Failed to send OTP. Please try again later.",
            }

        # Store eTP in database
        otp_hash = self.hash_otp(otp_code, phone)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.expiry_minutes
        )

        otp_record = OTP(
            phone=phone,
            otp_hash=otp_hash,
            expires_at=expires_at,
            reference_id=reference_id,
        )

        self.db.add(otp_record)
        self.db.commit()
        self.db.refresh(otp_record)

        return {
            "status": "success",
            "message": "OTP sent successfully",
            "reference_id": reference_id,
            "expires_in_minutes": self.expiry_minutes,
        }

    async def verify_otp(self, phone: str, otp_code: str) -> bool:
        """Verify OTP code."""
        result = await self.verify_otp_detailed(phone, otp_code)
        return result["valid"]

    async def verify_otp_detailed(
        self, phone: str, otp_code: str
    ) -> dict[str, Any]:
        """Verify OTP code with detailed result."""
        # Get the most recent OTP for this phone number
        statement = (
            select(OTP).where(OTP.phone == phone).order_by(desc(OTP.created_at))
        )
        otp_record = self.db.exec(statement).first()

        if not otp_record:
            return {
                "valid": False,
                "reason": "no_otp",
                "message": "No OTP found for this phone number",
            }

        # Check if already verified
        if otp_record.is_verified:
            return {
                "valid": False,
                "reason": "already_used",
                "message": "OTP has already been used",
            }

        # Check if expired
        now = datetime.now(timezone.utc)
        expires_at = otp_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            return {
                "valid": False,
                "reason": "expired",
                "message": "OTP has expired. Please request a new one",
            }

        # Increment attempts
        otp_record.attempts += 1

        # Check if max attempts reached
        if otp_record.attempts > self.max_attempts:
            self.db.commit()
            return {
                "valid": False,
                "reason": "max_attempts",
                "message": (
                    "Maximum verification attempts exceeded. Please "
                    "request a new OTP"
                ),
            }

        # Verify OTP hash
        if not self.verify_otp_hash(otp_code, phone, otp_record.otp_hash):
            self.db.commit()
            return {
                "valid": False,
                "reason": "invalid_code",
                "message": "Invalid OTP code. Please check and try again",
            }

        # Mark as verified
        otp_record.is_verified = True
        otp_record.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return {
            "valid": True,
            "reason": "success",
            "message": "OTP verified successfully",
        }

    async def invalidate_otp(self, phone: str) -> None:
        """Invalidate any existing OTP for the phone number."""
        statement = select(OTP).where(OTP.phone == phone, not OTP.is_verified)
        otp_records = self.db.exec(statement).all()

        for otp_record in otp_records:
            otp_record.is_verified = True
            otp_record.updated_at = datetime.now(timezone.utc)

        self.db.commit()

    async def get_otp_status(self, phone: str) -> dict[str, Any]:
        """Get OTP status for a phone number."""
        otp_record = self.get_valid_otp(phone)

        if not otp_record:
            return {
                "has_pending_otp": False,
                "attempts_remaining": self.max_attempts,
                "expires_at": None,
                "can_resend": await self.check_rate_limit(phone),
            }

        return {
            "has_pending_otp": True,
            "attempts_remaining": max(
                0, self.max_attempts - otp_record.attempts
            ),
            "expires_at": otp_record.expires_at.isoformat(),
            "can_resend": await self.check_rate_limit(phone),
        }
