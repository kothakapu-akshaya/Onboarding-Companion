# app/api/v1/endpoints/auth.py
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
)
from app.core.config import settings
from app.core.rbac_fastapi import get_user_roles, require_admin
from app.core.validators import (
    PasswordStrengthError,
    validate_password_strength,
)
from app.db.session import SessionDep
from app.models.role import Role
from app.models.user import User
from app.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
    UserReadWithRole,
)
from app.schemas.otp import (
    OTPLoginSendRequest,
    OTPLoginVerifyRequest,
    OTPResponse,
    OTPSignupResendRequest,
    OTPSignupSendRequest,
    OTPSignupVerifyRequest,
    TokenResponse,
)
from app.schemas.password_reset import (
    PasswordResetConfirmRequest,
    PasswordResetInitRequest,
    PasswordResetResponse,
)
from app.services.otp_service import OTPService

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


# Request/Response Models for Password Validation
class PasswordValidationRequest(BaseModel):
    """Request model for password strength validation."""

    password: str = Field(..., description="Password to validate")
    user_context: dict[str, str] | None = Field(
        None, description="User context for preventing predictable patterns"
    )


class PasswordValidationResponse(BaseModel):
    """Response model for password strength validation."""

    valid: bool = Field(..., description="Whether password meets requirements")
    score: int = Field(..., description="Password strength score (0-4)")
    message: str = Field(..., description="Validation message")
    suggestions: list[str] = Field(
        default_factory=list, description="Suggestions for improvement"
    )


@router.post(
    "/validate-password-strength", response_model=PasswordValidationResponse
)
async def validate_password_strength_endpoint(
    request: PasswordValidationRequest,
):
    """Validate password strength using zxcvbn algorithm.

    This endpoint validates password strength entropy-based analysis
    (NIST SP 800-63B compliant). It accepts optional user context
    (username, email, etc.) to detect predictable patterns.

    Args:
        request: PasswordValidationRequest containing password and
            optional user context

    Returns:
        PasswordValidationResponse with validation result and suggestions

    Raises:
        HTTPException: If validation fails with detailed error message
    """
    try:
        # Extract user inputs from context
        user_inputs = []
        if request.user_context:
            user_inputs = [
                v
                for v in request.user_context.values()
                if isinstance(v, str) and v.strip()
            ]

        # Validate password strength
        validate_password_strength(
            request.password, user_inputs=user_inputs if user_inputs else None
        )

        # If validation passed, get the score and feedback
        from zxcvbn import zxcvbn

        result = zxcvbn(
            request.password, user_inputs=user_inputs if user_inputs else None
        )
        score = result.get("score", 0)

        return PasswordValidationResponse(
            valid=True,
            score=score,
            message="Password is strong and meets all requirements",
            suggestions=[],
        )

    except PasswordStrengthError as e:
        # Password validation failed
        from zxcvbn import zxcvbn

        result = zxcvbn(
            request.password, user_inputs=user_inputs if user_inputs else None
        )
        score = result.get("score", 0)

        return PasswordValidationResponse(
            valid=False,
            score=score,
            message=e.message,
            suggestions=e.suggestions,
        )

    except Exception as e:
        logger.error(f"Error validating password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validating password strength",
        )


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(login_data: LoginRequest, session: SessionDep):
    """Authenticate user and return access token."""
    user = authenticate_user(session, login_data.phone, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login time
    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    # Get user's roles
    from app.models.associations import UserRoleLink
    from app.schemas import RoleRead

    statement = (
        select(Role).join(UserRoleLink).where(UserRoleLink.user_id == user.id)
    )
    roles = session.exec(statement).all()
    role_reads = [RoleRead.model_validate(role.model_dump()) for role in roles]

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        username=user.username,
        phone=user.phone,
        roles=role_reads,
    )


@router.get("/me", response_model=UserReadWithRole)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user information."""
    roles = get_user_roles(current_user.id)
    user_dict = current_user.model_dump()
    user_dict["roles"] = roles
    user_dict["role"] = next(
        (r for r in ("admin", "reviewer", "user", "system") if r in roles),
        roles[0] if roles else None,
    )
    return UserReadWithRole.model_validate(user_dict)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    """Change current user's password."""
    if not verify_password(
        password_data.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    session.add(current_user)
    session.commit()

    return MessageResponse(message="Password changed successfully")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    reset_data: PasswordResetRequest,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
):
    """Reset user password (admin functionality)."""
    statement = select(User).where(User.phone == reset_data.phone)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    session.add(user)
    session.commit()

    return MessageResponse(message="Password reset successfully")


@router.post("/login/send-otp", response_model=OTPResponse)
async def send_login_otp(request: OTPLoginSendRequest, session: SessionDep):
    """Send OTP to phone number for login via SMS."""
    try:
        # Check if user exists
        statement = select(User).where(User.phone == request.phone)
        user = session.exec(statement).first()

        if not user:
            # Instead of rejecting, prompt user to signup
            return OTPResponse(
                status="signup_required",
                message=(
                    "Phone number not found. Please use signup flow "
                    "to create an account."
                ),
                reference_id=None,
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        otp_service = OTPService(session)

        # Check rate limiting with detailed message
        rate_limit_result = await otp_service.check_rate_limit_detailed(
            request.phone
        )
        if not rate_limit_result["allowed"]:
            wait_minutes = rate_limit_result["wait_minutes"]
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. Please wait {wait_minutes} "
                    f"minute(s) before trying again."
                ),
            )

        # Send OTP
        result = await otp_service.send_otp(request.phone)

        if result["status"] == "success":
            return OTPResponse(
                status="success",
                message="OTP sent successfully",
                reference_id=result.get("reference_id"),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Failed to send OTP: "
                    f"{result.get('message', 'Unknown error')}"
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/login/verify-otp", response_model=TokenResponse)
async def verify_login_otp(request: OTPLoginVerifyRequest, session: SessionDep):
    """Verify OTP for login and generate JWT token."""
    try:
        otp_service = OTPService(session)

        # Verify OTP with detailed error messaging
        otp_result = await otp_service.verify_otp_detailed(
            request.phone, request.otp_code
        )

        if not otp_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_result["message"],
            )

        # Get user (user should exist since we checked in send-otp)
        statement = select(User).where(User.phone == request.phone)
        user = session.exec(statement).first()

        if not user:
            # This should not happen if send-otp was called first
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        session.add(user)
        session.commit()

        # Get user's roles through association table
        from app.models.associations import UserRoleLink
        from app.models.role import Role
        from app.schemas import RoleRead

        statement = (
            select(Role)
            .join(UserRoleLink)
            .where(UserRoleLink.user_id == user.id)
        )
        roles = session.exec(statement).all()

        # Convert Role objects to RoleRead objects
        role_reads = [
            RoleRead.model_validate(role.model_dump()) for role in roles
        ]

        # Generate JWT token
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=str(user.id),
            username=user.username,
            phone=user.phone,
            roles=role_reads,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/login/resend-otp", response_model=OTPResponse)
async def resend_login_otp(request: OTPLoginSendRequest, session: SessionDep):
    """Resend OTP to phone number for login."""
    try:
        # Check if user exists (same as send-otp)
        statement = select(User).where(User.phone == request.phone)
        user = session.exec(statement).first()

        if not user:
            # Instead of rejecting, prompt user to signup
            # (consistent with send-otp behavior)
            return OTPResponse(
                status="signup_required",
                message=(
                    "Phone number not found. Please use signup flow "
                    "to create an account."
                ),
                reference_id=None,
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        otp_service = OTPService(session)

        # Check rate limiting for resend
        if not await otp_service.check_rate_limit(request.phone):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        # Invalidate existing OTP
        await otp_service.invalidate_otp(request.phone)

        # Send new OTP
        result = await otp_service.send_otp(request.phone)

        if result["status"] == "success":
            return OTPResponse(
                status="success",
                message="OTP resent successfully",
                reference_id=result.get("reference_id"),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Failed to resend OTP: "
                    f"{result.get('message', 'Unknown error')}"
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/forgot-password/init", response_model=PasswordResetResponse)
async def initiate_password_reset(
    request: PasswordResetInitRequest, session: SessionDep
):
    """Initiate password reset process by sending OTP to user's phone."""
    try:
        # Check if user exists
        statement = select(User).where(User.phone == request.phone)
        user = session.exec(statement).first()

        # Always return success for privacy reasons
        # (don't reveal if user exists)
        if not user or not user.is_active:
            logger.info(
                f"Password reset attempt for non-existent/inactive user: "
                f"{request.phone}"
            )
            return PasswordResetResponse(
                status="success",
                message=(
                    "If the phone number is registered, "
                    "you will receive an OTP shortly"
                ),
            )

        otp_service = OTPService(session)

        # Check rate limiting with detailed message
        rate_limit_result = await otp_service.check_rate_limit_detailed(
            request.phone
        )
        if not rate_limit_result["allowed"]:
            wait_minutes = rate_limit_result["wait_minutes"]
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. Please wait {wait_minutes} "
                    f"minute(s) before trying again."
                ),
            )

        # Send OTP
        result = await otp_service.send_otp(request.phone)

        if result["status"] == "success":
            return PasswordResetResponse(
                status="success",
                message=(
                    "If the phone number is registered, "
                    "you will receive an OTP shortly"
                ),
                reference_id=result.get("reference_id"),
            )
        else:
            # Don't reveal SMS sending failures for privacy
            logger.error(
                f"Failed to send password reset OTP: {result.get('message')}"
            )
            return PasswordResetResponse(
                status="success",
                message=(
                    "If the phone number is registered, "
                    "you will receive an OTP shortly"
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating password reset: {str(e)}")
        # Don't reveal internal errors for privacy
        return PasswordResetResponse(
            status="success",
            message=(
                "If the phone number is registered, "
                "you will receive an OTP shortly"
            ),
        )


@router.post("/forgot-password/confirm", response_model=PasswordResetResponse)
async def confirm_password_reset(
    request: PasswordResetConfirmRequest, session: SessionDep
):
    """Confirm password reset with OTP and set new password."""
    try:
        otp_service = OTPService(session)

        # Verify OTP with detailed error messaging
        otp_result = await otp_service.verify_otp_detailed(
            request.phone, request.otp_code
        )

        if not otp_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_result["message"],
            )

        # Get user (should exist if OTP was sent successfully)
        statement = select(User).where(User.phone == request.phone)
        user = session.exec(statement).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
            )

        # Prevent using the same password as current password
        if verify_password(request.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be the same as current password",
            )

        # Update password
        user.hashed_password = get_password_hash(request.new_password)
        session.add(user)
        session.commit()

        logger.info(f"Password reset successful for user: {user.phone}")

        return PasswordResetResponse(
            status="success", message="Password reset successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming password reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/signup/send-otp", response_model=OTPResponse)
async def send_signup_otp(request: OTPSignupSendRequest, session: SessionDep):
    """Send OTP to phone number for signup (no user registration required)."""
    try:
        # Check if user already exists
        statement = select(User).where(User.phone == request.phone)
        existing_user = session.exec(statement).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this phone number already exists",
            )

        # Check if email already exists
        statement = select(User).where(User.email == request.email)
        existing_email = session.exec(statement).first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email address already exists",
            )

        otp_service = OTPService(session)

        # Check rate limiting with detailed message
        rate_limit_result = await otp_service.check_rate_limit_detailed(
            request.phone
        )
        if not rate_limit_result["allowed"]:
            wait_minutes = rate_limit_result["wait_minutes"]
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. Please wait {wait_minutes} "
                    f"minute(s) before trying again."
                ),
            )

        # Send OTP for signup
        result = await otp_service.send_signup_otp(request.phone)

        if result["status"] == "success":
            return OTPResponse(
                status="success",
                message="OTP sent successfully for signup",
                reference_id=result.get("reference_id"),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Failed to send OTP: "
                    f"{result.get('message', 'Unknown error')}"
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending signup OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/signup/verify-otp", response_model=TokenResponse)
async def verify_signup_otp(
    request: OTPSignupVerifyRequest, session: SessionDep
):
    """Verify OTP and create new user account."""
    try:
        # Validate consent requirement
        if not request.has_given_consent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User consent is required to create an account",
            )

        # Check if user already exists
        statement = select(User).where(User.phone == request.phone)
        existing_user = session.exec(statement).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this phone number already exists",
            )

        # Generate a unique temporary username (deferred to Step 2)
        # Use a prefix that identifies it as temporary, followed by random hex
        temp_username = f"user_{uuid.uuid4().hex[:12]}"

        # Ensure the generated username is unique (extremely unlikely to
        # collide but safe to check)
        while session.exec(
            select(User).where(User.username == temp_username)
        ).first():
            temp_username = f"user_{uuid.uuid4().hex[:12]}"

        effective_username = temp_username

        # Check if email already exists
        statement = select(User).where(User.email == request.email)
        existing_email = session.exec(statement).first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email address already exists",
            )

        otp_service = OTPService(session)

        # Verify OTP with detailed error messaging
        otp_result = await otp_service.verify_otp_detailed(
            request.phone, request.otp_code
        )

        if not otp_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=otp_result["message"],
            )

        # All new users get the regular user role (role_id=3) by default
        # Role assignment is admin-only functionality

        # Create new user with minimal step-1 fields
        from datetime import datetime

        from app.core.auth import get_password_hash

        user = User(
            phone=request.phone,
            username=effective_username,
            name=request.name,
            email=request.email,
            hashed_password=get_password_hash(request.password),
            is_active=True,
            has_given_consent=True,
            is_intern=request.is_intern,
        )

        session.add(user)
        session.flush()  # Get the user ID before committing

        # Assign default regular user role (role_id=3) to new users
        from app.models.associations import UserRoleLink

        # All signups get regular user role by default - admin can change
        # roles later
        default_role_id = 3  # Regular user role
        user_role_link = UserRoleLink(user_id=user.id, role_id=default_role_id)
        session.add(user_role_link)

        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        session.add(user)
        session.commit()
        session.refresh(user)

        # Get user's roles for response
        from app.schemas import RoleRead

        statement = (
            select(Role)
            .join(UserRoleLink)
            .where(UserRoleLink.user_id == user.id)
        )
        roles = session.exec(statement).all()

        # Convert Role objects to RoleRead objects
        role_reads = [
            RoleRead.model_validate(role.model_dump()) for role in roles
        ]

        # Generate JWT token
        from app.core.auth import create_access_token

        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=str(user.id),
            username=user.username,
            phone=user.phone,
            roles=role_reads,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying signup OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/signup/resend-otp", response_model=OTPResponse)
async def resend_signup_otp(
    request: OTPSignupResendRequest, session: SessionDep
):
    """Resend OTP to phone number for signup."""
    try:
        # Check if user already exists
        statement = select(User).where(User.phone == request.phone)
        existing_user = session.exec(statement).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this phone number already exists",
            )

        otp_service = OTPService(session)

        # Check rate limiting for resend
        if not await otp_service.check_rate_limit(request.phone):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        # Invalidate existing OTP
        await otp_service.invalidate_otp(request.phone)

        # Send new OTP for signup
        result = await otp_service.send_signup_otp(request.phone)

        if result["status"] == "success":
            return OTPResponse(
                status="success",
                message="OTP resent successfully for signup",
                reference_id=result.get("reference_id"),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Failed to resend OTP: "
                    f"{result.get('message', 'Unknown error')}"
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending signup OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
