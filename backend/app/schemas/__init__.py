"""API schemas package."""

from datetime import date, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
)

from app.core.language_utils import (
    LANGUAGE_NOT_AVAILABLE,
    LANGUAGE_UNDETERMINED,
    normalize_language_name,
)
from app.core.validators import validate_password_strength
from app.models.institution import (
    CollegeType,
    District,
    ManagementType,
    Medium,
    Mode,
)

# Import modular validation schemas
from .auth_validation import (
    OTPValidation,
    PasswordChangeValidation,
    TokenValidation,
    UserLoginValidation,
    UserProfileUpdateValidation,
    UserRegistrationValidation,
    UserSignupStep1Validation,
)

# Import extracted text schemas
from .extracted_text import (
    ExtractedText,
    ExtractedTextCreate,
    ExtractedTextType,
    ExtractedTextUpdate,
    ExtractedTextUpdateResponse,
    TextSegment,
)

# Import geographic schemas
from .geo_schemas import Coordinates
from .rag import (
    KnowledgeResponse,
    KnowledgeUpdateRequest,
    KnowledgeUpdateResponse,
    RAGStatus,
    RetrievalRequest,
    RetrievalResponse,
)

# Import record history schemas
from .record_history import (
    RecordDiffRead,
    RecordFieldHistoryRead,
    RecordHistoryRead,
    RecordRestoreCreate,
    RecordRestoreRead,
    RecordVersionRead,
    StreakData,
    UserStreaks,
    VersionSummaryRead,
)
from .upload_validation import (
    AudioContentValidation,
    AudioFileValidation,
    BatchUploadValidation,
    ChunkedUploadValidation,
    ContentValidationBase,
    FileUploadValidation,
    ImageContentValidation,
    ImageFileValidation,
    TextContentValidation,
    TextFileValidation,
    VideoContentValidation,
    VideoFileValidation,
)

# Explicit exports to fix ruff F401 warnings
__all__ = [
    # Auth validation
    "UserRegistrationValidation",
    "UserSignupStep1Validation",
    "UserLoginValidation",
    "UserProfileUpdateValidation",
    "PasswordChangeValidation",
    "OTPValidation",
    "TokenValidation",
    # Upload validation
    "ContentValidationBase",
    "AudioContentValidation",
    "VideoContentValidation",
    "ImageContentValidation",
    "TextContentValidation",
    "FileUploadValidation",
    "AudioFileValidation",
    "VideoFileValidation",
    "ImageFileValidation",
    "TextFileValidation",
    "BatchUploadValidation",
    "ChunkedUploadValidation",
    # Other schemas defined in this file
    "filter_user_privacy",
    "RoleEnum",
    "MediaType",
    "ReleaseRights",
    "Gender",
    "FieldPrivacy",
    "LanguageCreateRequest",
    "LanguageProficiency",
    "LanguageProficiencyEntry",
    "LanguageProficiencies",
    "SocialMediaPlatform",
    "SocialMediaProfileEntry",
    "SocialMediaProfiles",
    "PlacesLived",
    "Token",
    "TokenData",
    "LoginRequest",
    "PasswordChangeRequest",
    "UserPasswordChangeRequest",
    "PasswordResetRequest",
    "RoleBase",
    "RoleCreate",
    "RoleRead",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserRead",
    "UserReadWithRole",
    "UserWithRoles",
    "UserRoleAssignment",
    "UserRoleResponse",
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryRead",
    "CategorySuggest",
    "RecordBase",
    "RecordCreate",
    "RecordUpdate",
    "RecordRead",
    "MessageResponse",
    "ErrorResponse",
    "ContributionResponse",
    "ContirbutionMediaCountResponse",
    "ContributionRead",
    "ContributionFilterRead",
    "RecordUrlResponse",
    "RAGStatus",
    "KnowledgeResponse",
    "KnowledgeUpdateRequest",
    "KnowledgeUpdateResponse",
    "RetrievalRequest",
    "RetrievalResponse",
    "Coordinates",
    "LocationRequest",
    "LocationResponse",
    "RecordReviewFilters",
    "RecordReviewRequest",
    "RecordReviewResponse",
    # Record history schemas
    "RecordHistoryRead",
    "RecordFieldHistoryRead",
    "RecordVersionRead",
    "RecordDiffRead",
    "RecordRestoreCreate",
    "RecordRestoreRead",
    "VersionSummaryRead",
    # User streak schemas
    "StreakData",
    "UserStreaks",
    # Follow relationship schemas
    "FollowersList",
    "FollowingList",
    # Extracted text schemas
    "ExtractedTextType",
    "TextSegment",
    "ExtractedText",
    "ExtractedTextCreate",
    "ExtractedTextUpdate",
    "ExtractedTextUpdateResponse",
    # Location schemas
    "LocationRequest",
    "LocationResponse",
    # Institution schemas
    "CourseRead",
    "CourseCreate",
    "InstitutionRowRead",
    "InstitutionRead",
    "InstitutionCreate",
    "InstitutionEnums",
    "HardwareDetails",
]


# Institution schemas


class CourseRead(BaseModel):
    """Course read schema."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    course_name: str | None = None
    option_a_bucket: str | None = None
    option_b_bucket: str | None = None
    option_c_bucket: str | None = None
    option_d_bucket: str | None = None
    cbcs: bool | None = None
    revised_intake: int | None = None
    mode: Mode | None = None


class CourseCreate(BaseModel):
    """Course creation schema."""

    course_name: str | None = None
    option_a_bucket: str | None = None
    option_b_bucket: str | None = None
    option_c_bucket: str | None = None
    option_d_bucket: str | None = None
    cbcs: bool | None = None
    revised_intake: int | None = None
    mode: Mode | None = None


class InstitutionRowRead(BaseModel):
    """Institution row read schema."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    college_name: str
    university_name: str
    academic_stream: str | None = None
    medium: Medium | None = None
    district: District | None = None
    college_type: CollegeType | None = None
    courses: list[CourseRead] = []


class InstitutionRead(InstitutionRowRead):
    """Institution read schema."""

    address: str | None = None
    code: int | None = None
    management_type: ManagementType | None = None


class InstitutionCreate(BaseModel):
    """Institution creation schema."""

    university_name: str
    college_name: str
    academic_stream: str | None = None
    district: District | None = None
    address: str | None = None
    code: int | None = None
    college_type: CollegeType | None = None
    management_type: ManagementType | None = None
    medium: Medium | None = None
    course_name: str | None = None
    option_a_bucket: str | None = None
    option_b_bucket: str | None = None
    option_c_bucket: str | None = None
    option_d_bucket: str | None = None
    mode: Mode | None = None
    cbcs: bool | None = None
    revised_intake: int | None = None
    courses: list[CourseCreate] = []


class InstitutionEnums(BaseModel):
    """Institution enum values schema."""

    districts: list[str]
    college_types: list[str]
    management_types: list[str]
    mediums: list[str]
    modes: list[str]
    academic_streams: list[str]


class HardwareDetails(BaseModel):
    """Hardware details schema."""

    workstation_os: str | None = Field(None, max_length=100)
    workstation_ram: str | None = Field(None, max_length=100)
    mobile_os: str | None = Field(None, max_length=100)
    mobile_ram: str | None = Field(None, max_length=100)
    internet_speed: str | None = Field(None, max_length=100)
    daily_data_limit: str | None = Field(None, max_length=100)


class RoleEnum(str, Enum):
    """User role enumeration."""

    admin = "admin"
    user = "user"
    reviewer = "reviewer"
    system = "system"


class MediaType(str, Enum):
    """Media type enumeration."""

    text = "text"
    audio = "audio"
    video = "video"
    image = "image"
    document = "document"


class ReleaseRights(str, Enum):
    """Release rights enumeration."""

    creator = "creator"
    others = "others"
    downloaded = "downloaded"
    NA = "NA"


class Gender(str, Enum):
    """Gender enumeration."""

    male = "male"
    female = "female"
    other = "other"


class FieldPrivacy(str, Enum):
    """Field privacy enumeration."""

    public = "public"
    private = "private"


class LanguageProficiency(str, Enum):
    """Language proficiency level enumeration."""

    basic = "basic"
    intermediate = "intermediate"
    proficient = "proficient"


class LanguageProficiencyEntry(BaseModel):
    """Individual language proficiency entry."""

    language: str
    proficiency: LanguageProficiency

    @field_validator("language")
    @classmethod
    def normalize_language(cls, v: str) -> str:
        return normalize_language_name(v)


class LanguageProficiencies(BaseModel):
    """Collection of language proficiencies with validation."""

    proficiencies: list[LanguageProficiencyEntry] = Field(..., min_length=1)

    @field_validator("proficiencies")
    @classmethod
    def validate_unique_languages(
        cls, v: list[LanguageProficiencyEntry]
    ) -> list[LanguageProficiencyEntry]:
        """Ensure no duplicate languages."""
        languages = [entry.language for entry in v]
        if len(languages) != len(set(languages)):
            raise ValueError("Duplicate languages are not allowed")
        return v

    @field_validator("proficiencies")
    @classmethod
    def validate_no_na_language(
        cls, v: list[LanguageProficiencyEntry]
    ) -> list[LanguageProficiencyEntry]:
        """Ensure NA/undetermined language is not used in proficiencies."""
        for entry in v:
            if entry.language in (
                LANGUAGE_NOT_AVAILABLE,
                LANGUAGE_UNDETERMINED,
            ):
                raise ValueError("Cannot set proficiency for reserved language")
        return v


class SocialMediaPlatform(str, Enum):
    """Social media platform enumeration."""

    instagram = "instagram"
    x = "x"
    linkedin = "linkedin"
    facebook = "facebook"
    youtube = "youtube"
    tiktok = "tiktok"
    custom = "custom"


class SocialMediaProfileEntry(BaseModel):
    """Individual social media profile entry."""

    platform: SocialMediaPlatform
    url: HttpUrl = Field(..., description="Full URL to the profile")


class SocialMediaProfiles(BaseModel):
    """Collection of social media profiles with validation."""

    profiles: list[SocialMediaProfileEntry] = Field(default_factory=list)

    @field_validator("profiles")
    @classmethod
    def validate_unique_platforms(
        cls, v: list[SocialMediaProfileEntry]
    ) -> list[SocialMediaProfileEntry]:
        """Ensure no duplicate platforms."""
        platforms = [entry.platform for entry in v]
        if len(platforms) != len(set(platforms)):
            raise ValueError("Duplicate platforms are not allowed")
        return v


class PlacesLived(BaseModel):
    """Collection of places where user has lived."""

    places: list[Coordinates] = Field(default_factory=list)

    @field_validator("places")
    @classmethod
    def validate_places_limit(cls, v: list[Coordinates]) -> list[Coordinates]:
        """Limit the number of places."""
        if len(v) > 20:
            raise ValueError("Cannot specify more than 20 places")
        return v


# Authentication schemas
class Token(BaseModel):
    """Authentication token schema."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token payload data schema."""

    user_id: str | None = None


class LoginRequest(BaseModel):
    """Login request schema."""

    phone: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1)


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)


class UserPasswordChangeRequest(BaseModel):
    """User password change request schema."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)

    def model_post_init(self, __context) -> None:
        """Validate that passwords match."""
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""

    phone: str = Field(..., min_length=1, max_length=20)
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)


# Role schemas
class RoleBase(BaseModel):
    """Role base schema."""

    name: RoleEnum
    description: str | None = None


class RoleCreate(RoleBase):
    """Role creation schema."""

    pass


class RoleRead(RoleBase):
    """Role read schema."""

    id: int
    model_config = ConfigDict(from_attributes=True)


# User schemas - simplified to use modular validation
class UserBase(BaseModel):
    """User base schema."""

    phone: str = Field(..., min_length=10, max_length=20)
    username: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., max_length=100)
    email: EmailStr | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    current_place: str | None = Field(None, max_length=200)
    is_intern: bool = Field(default=False)


class UserCreate(UserRegistrationValidation):
    """User creation using modular validation."""

    language_proficiencies: LanguageProficiencies | None = None
    role_ids: list[int] = Field(default=[2])  # Default to user role (id=2)


class UserUpdate(BaseModel):
    """User update schema."""

    username: str | None = Field(None, min_length=3, max_length=50)
    name: str | None = None
    email: EmailStr | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    current_place: str | None = None
    profile_picture_path: str | None = Field(None, max_length=255)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Validate username format."""
        if v is None or v.strip() == "":
            return None

        import regex

        cleaned = v.strip().lower()

        if len(cleaned) < 3:
            raise ValueError("Username must be at least 3 characters long")

        if len(cleaned) > 50:
            raise ValueError("Username must not exceed 50 characters")

        # Username can only contain lowercase letters, numbers, and underscores
        if not regex.match(r"^[a-z0-9_]+$", cleaned):
            raise ValueError(
                "Username can only contain lowercase letters, numbers, "
                "and underscores"
            )

        return cleaned

    @field_validator("profile_picture_path")
    @classmethod
    def validate_image_path(cls, v: str | None) -> str | None:
        """Validate that the file path points to an image file."""
        if v is None:
            return v

        # Check file extension
        valid_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
            ".tiff",
            ".svg",
        }
        if not any(v.lower().endswith(ext) for ext in valid_extensions):
            ext_list = ", ".join(valid_extensions)
            raise ValueError(
                "File must be an image with one of these extensions: "
                f"{ext_list}"
            )

        return v

    short_bio: str | None = Field(None, max_length=500)
    profession: str | None = Field(None, max_length=200)
    organisation: str | None = Field(None, max_length=200)
    places_lived: PlacesLived | None = None
    from_place: Coordinates | None = None
    social_media_profiles: SocialMediaProfiles | None = None
    language_proficiencies: LanguageProficiencies | None = None
    is_active: bool | None = None
    has_given_consent: bool | None = None
    is_intern: bool | None = None
    phone_privacy: FieldPrivacy | None = None
    email_privacy: FieldPrivacy | None = None
    # Internship-specific fields
    rural_area_access: str | None = Field(None, max_length=500)
    permanent_postal_address: str | None = Field(None, max_length=500)
    institution_id: UUID | None = None
    current_year_of_study: str | None = Field(None, max_length=50)
    college_roll_number: str | None = Field(None, max_length=100)
    task_registered_id: str | None = Field(None, max_length=100)
    resume_record_id: UUID | None = None
    hardware_details: HardwareDetails | None = None
    has_completed_ai_courses: str | None = Field(None, max_length=50)
    ai_courses_list: str | None = Field(None, max_length=1000)


class UserRead(UserBase):
    """User read schema."""

    id: UUID
    phone: str | None = None
    profile_picture_path: str | None = None
    short_bio: str | None = None
    profession: str | None = None
    organisation: str | None = None
    places_lived: PlacesLived | None = None
    from_place: Coordinates | None = None
    social_media_profiles: SocialMediaProfiles | None = None
    language_proficiencies: LanguageProficiencies | None = None
    is_active: bool
    has_given_consent: bool
    phone_privacy: FieldPrivacy
    email_privacy: FieldPrivacy
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    # Internship-specific fields
    rural_area_access: str | None = None
    permanent_postal_address: str | None = None
    institution_id: UUID | None = None
    current_year_of_study: str | None = None
    college_roll_number: str | None = None
    task_registered_id: str | None = None
    resume_record_id: UUID | None = None
    hardware_details: HardwareDetails | None = None
    has_completed_ai_courses: str | None = None
    ai_courses_list: str | None = None

    @field_validator("language_proficiencies", mode="before")
    @classmethod
    def parse_language_proficiencies(cls, v):
        """Parse JSON string to LanguageProficiencies object."""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            try:
                data = json.loads(v)
                return LanguageProficiencies(**data)
            except (json.JSONDecodeError, ValueError):
                return None
        return v

    @field_validator("social_media_profiles", mode="before")
    @classmethod
    def parse_social_media_profiles(cls, v):
        """Parse JSON string to SocialMediaProfiles object."""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            try:
                data = json.loads(v)
                return SocialMediaProfiles(**data)
            except (json.JSONDecodeError, ValueError):
                return None
        return v

    @field_validator("from_place", mode="before")
    @classmethod
    def parse_from_place(cls, v):
        """Parse JSON string to Coordinates object."""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            try:
                data = json.loads(v)
                return Coordinates(**data)
            except (json.JSONDecodeError, ValueError):
                return None
        return v

    @field_validator("places_lived", mode="before")
    @classmethod
    def parse_places_lived(cls, v):
        """Parse JSON string to PlacesLived object."""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            try:
                data = json.loads(v)
                return PlacesLived(**data)
            except (json.JSONDecodeError, ValueError):
                return None
        return v

    @field_validator("hardware_details", mode="before")
    @classmethod
    def parse_hardware_details(cls, v):
        """Parse JSON string to HardwareDetails object."""
        if v is None:
            return None
        if isinstance(v, str):
            import json

            try:
                data = json.loads(v)
                return HardwareDetails(**data)
            except (json.JSONDecodeError, ValueError):
                return None
        return v


class UserReadWithRole(UserRead):
    """UserRead extended with resolved role fields for auth/me and profile."""

    role: str | None = None
    roles: list[str] = []


class UserWithRoles(UserRead):
    """User with roles schema."""

    roles: list[RoleRead] = []


# User role management schemas
class UserRoleAssignment(BaseModel):
    """User role assignment schema."""

    user_id: UUID
    role_ids: list[int]


class UserRoleResponse(BaseModel):
    """User role response schema."""

    user_id: UUID
    roles: list[RoleRead]
    model_config = ConfigDict(from_attributes=True)


class LanguageCreateRequest(BaseModel):
    """Request schema for creating a language registry entry."""

    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return normalize_language_name(v)


# Category schemas
class CategoryBase(BaseModel):
    """Category base schema."""

    name: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    published: bool = False
    rank: int = 0
    approved: bool = False  # Whether the category has been approved by an admin


class CategoryCreate(CategoryBase):
    """Category creation schema."""

    pass


class CategoryUpdate(BaseModel):
    """Category update schema."""

    name: str | None = None
    title: str | None = None
    description: str | None = None
    published: bool | None = None
    rank: int | None = None
    approved: bool | None = None


class CategoryRead(CategoryBase):
    """Category read schema."""

    id: UUID
    suggested_by: UUID | None = None  # User who suggested the category
    approved_by: UUID | None = None  # Admin who approved the category
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CategorySuggest(BaseModel):
    """Schema for when users suggest new categories."""

    name: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    # Note: published, rank, and approved are not included -
    # they will be set by server


# Record schemas - simplified to use modular validation
class RecordBase(ContentValidationBase):
    """Record base using modular content validation."""

    media_type: MediaType
    file_url: str | None = Field(None, max_length=500)
    file_name: str | None = Field(None, max_length=255)
    file_size: int | None = Field(None, ge=0)
    status: str = Field(default="pending", max_length=20)
    reviewed: bool = Field(default=False)
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    source_label: str | None = Field(
        None, max_length=200, description="Label for the source of the record"
    )
    source_url: HttpUrl | None = Field(
        None, description="URL for the source of the record"
    )

    @field_validator("source_url")
    @classmethod
    def validate_source_url_length(cls, v: HttpUrl | None) -> HttpUrl | None:
        if v is not None and len(str(v)) > 500:
            raise ValueError("Source URL must not exceed 500 characters")
        return v

    @field_validator("file_size")
    @classmethod
    def validate_file_size(cls, v: int | None, info) -> int | None:
        """Validate file size based on media type."""
        if v is None:
            return None

        # Get media type from the model context
        media_type = info.data.get("media_type") if info.data else None

        if media_type == MediaType.audio:
            max_size = 500 * 1024 * 1024  # 500MB for audio
        elif media_type == MediaType.video:
            max_size = 2 * 1024 * 1024 * 1024  # 2GB for video
        elif media_type == MediaType.image:
            max_size = 50 * 1024 * 1024  # 50MB for images
        else:  # text
            max_size = 10 * 1024 * 1024  # 10MB for text files

        from app.core.validators import validate_file_size

        return validate_file_size(v, max_size)


class RecordCreate(RecordBase):
    """Record creation schema."""

    user_id: UUID
    category_ids: list[UUID] = Field(default_factory=list)
    tagged_usernames: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    record_tags: list[str] = Field(default_factory=list)
    device_id: str | None = Field(
        None,
        max_length=255,
        description=(
            "Client-generated device identifier of the contributing device, "
            "as registered via the devices endpoint"
        ),
    )


class RecordReadBase(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    media_type: MediaType | None = None
    file_url: str | None = Field(None, max_length=500)
    file_name: str | None = Field(None, max_length=255)
    file_size: int | None = Field(None, ge=0)
    status: str | None = Field(None, max_length=20)
    location: Coordinates | None = None  # PostGIS Point coordinates
    reviewed: bool | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    release_rights: ReleaseRights | None = None
    creator: str | None = Field(None, max_length=200)
    language: str | None = None
    published_date: date | None = Field(
        None, description="Published/event date of the record content"
    )
    source_label: str | None = Field(
        None, max_length=200, description="Label for the source of the record"
    )
    source_url: HttpUrl | None = Field(
        None, description="URL for the source of the record"
    )
    speech_not_detected: bool = Field(
        default=False,
        description="Flag for corrupt audio/video with no usable audio track",
    )

    @field_validator("source_url")
    @classmethod
    def validate_source_url_length(cls, v: HttpUrl | None) -> HttpUrl | None:
        if v is not None and len(str(v)) > 500:
            raise ValueError("Source URL must not exceed 500 characters")
        return v


class RecordUpdate(RecordReadBase):
    """Record update schema."""

    tagged_usernames: list[str] | None = None
    hashtags: list[str] | None = None
    record_tags: list[str] | None = None


class RecordRead(RecordReadBase):
    """Record read schema."""

    uid: UUID
    user_id: UUID
    username: str | None = Field(
        None, description="Username of the record creator"
    )
    device_uid: UUID | None = Field(
        None, description="Device the record was contributed from, if known"
    )
    category_ids: list[UUID] = Field(default_factory=list)
    tagged_usernames: list[str] | None = None
    hashtags: list[str] | None = None
    record_tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    duration_seconds: int | None = Field(
        None, ge=0
    )  # Duration in seconds (read-only)

    # Extracted text field
    extracted_text: dict | None = Field(
        None,
        description=(
            "Extracted text from OCR/ASR/Captioning "
            "(versioned via RecordHistory)"
        ),
    )
    extracted_text_source_record_id: UUID | None = Field(
        None,
        description=(
            "If non-null, the extracted text is borrowed from a sibling "
            "record with this UID (same file_hash). Null when the text "
            "belongs to this record."
        ),
    )

    @field_validator("extracted_text", mode="before")
    @classmethod
    def convert_extracted_text_to_dict(cls, v):
        """Convert ExtractedText model instance to dict for API response."""
        if v is None:
            return None

        if isinstance(v, dict):
            return v

        if hasattr(v, "model_dump"):
            data = v.model_dump()
            if "extraction_metadata" in data:
                data["metadata"] = data.pop("extraction_metadata")
            return data

        if hasattr(v, "__dict__"):
            data = {
                k: val for k, val in v.__dict__.items() if not k.startswith("_")
            }
            if "extraction_metadata" in data:
                data["metadata"] = data.pop("extraction_metadata")
            return data

        return v

    model_config = ConfigDict(from_attributes=True)

    @field_validator("location", mode="before")
    @classmethod
    def convert_wkb_to_coordinates(cls, v):
        # If the location from the database is None, we're done.
        if v is None:
            return None

        # If the value is a WKBElement (the special database type)...
        if isinstance(v, WKBElement):
            # ...convert it to a Shapely Point object...
            point = to_shape(v)
            # ...and return the simple dictionary that your
            # Coordinates model understands.
            return {"latitude": point.y, "longitude": point.x}

        # If the value is already a dictionary (e.g., from another source),
        # pass it along.
        return v


# Response schemas
class MessageResponse(BaseModel):
    """Message response schema."""

    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str


# contributions Schema
class ContributionResponse(BaseModel):
    """Contribution response schema."""

    id: UUID
    size: int  # in KB
    category_ids: list[UUID] = Field(default_factory=list)
    reviewed: bool
    title: str
    description: str | None = None
    duration: int | None = None
    timestamp: datetime | None = None
    location: Coordinates | None = None
    release_rights: ReleaseRights | None = None
    creator: str | None = None
    language: str | None = None
    file_hash: str | None = None
    snr_frequency: float | None = None
    speech_not_detected: bool = False
    tagged_usernames: list[str] | None = None
    hashtags: list[str] | None = None
    extracted_text_source_record_id: UUID | None = Field(
        None,
        description=(
            "If non-null, the extracted text is borrowed from a sibling "
            "record with this UID (same file_hash)."
        ),
    )
    record_tags: list[str] | None = None


class ContirbutionMediaCountResponse(BaseModel):
    """Contribution media count response schema."""

    text: int
    audio: int
    image: int
    video: int
    document: int


class ContributionRead(BaseModel):
    """Contribution read schema."""

    user_id: UUID
    total_contributions: int
    contributions_by_media_type: ContirbutionMediaCountResponse
    audio_contributions: list[ContributionResponse] | None = None
    video_contributions: list[ContributionResponse] | None = None
    text_contributions: list[ContributionResponse] | None = None
    image_contributions: list[ContributionResponse] | None = None
    document_contributions: list[ContributionResponse] | None = None
    audio_duration: int
    video_duration: int
    credits: float
    document_pages: int = 0
    compute_audio_duration: int = 0
    compute_audio_count: int = 0
    compute_video_duration: int = 0
    compute_video_count: int = 0
    compute_text_count: int = 0
    compute_document_count: int = 0
    compute_image_count: int = 0
    edit_audio_count: int = 0
    edit_video_count: int = 0
    edit_text_count: int = 0
    edit_document_count: int = 0
    edit_image_count: int = 0
    review_audio_count: int = 0
    review_video_count: int = 0
    review_text_count: int = 0
    review_document_count: int = 0
    review_image_count: int = 0


class ContributionFilterRead(BaseModel):
    """Contribution filter read schema."""

    user_id: UUID
    total_contributions: int
    contributions: list[ContributionResponse] | None = None


class RecordUrlResponse(BaseModel):
    """Record URL response schema."""

    record_url: str


class LocationRequest(BaseModel):
    """Location request schema."""

    latitude: float = Field(
        ..., ge=-90, le=90, description="Latitude coordinate"
    )
    longitude: float = Field(
        ..., ge=-180, le=180, description="Longitude coordinate"
    )


class LocationResponse(BaseModel):
    """Location response schema."""

    formatted_address: str
    country: str | None = None
    state: str | None = None
    city: str | None = None
    postal_code: str | None = None
    latitude: float
    longitude: float


class RecordReviewFilters(BaseModel):
    """Filters for record review endpoint."""

    language: list[str] | None = Field(
        None, description="Filter by languages (multiple values allowed)"
    )
    media_type: list[MediaType] | None = Field(
        None, description="Filter by media types (multiple values allowed)"
    )
    category_ids: list[UUID] | None = Field(
        None,
        description=(
            "Filter by category IDs "
            "(returns records with ANY of the specified categories)"
        ),
    )
    source_label: str | None = Field(
        None, max_length=200, description="Filter by source label"
    )
    release_rights: ReleaseRights | None = Field(
        None, description="Filter by release rights type"
    )
    published_date: date | None = Field(
        None, description="Filter by published date"
    )
    is_fully_proofread: bool | None = Field(
        None,
        description=(
            "Filter by fully proofread status "
            "(True=proofread, False=unproofread)"
        ),
    )
    is_fully_validated: bool | None = Field(
        None,
        description=(
            "Filter by fully validated status "
            "(True=validated, False=unvalidated)"
        ),
    )
    extraction_type: ExtractedTextType | None = Field(
        None,
        description="Filter by extraction type (ocr, asr, caption, manual)",
    )
    model_name: str | None = Field(
        None, max_length=100, description="Filter by model name"
    )
    version: Literal["initial", "latest"] | None = Field(
        None,
        description=(
            "Filter by version: 'initial' (version 0) "
            "or 'latest' (current version)"
        ),
    )
    lock: bool | None = Field(
        None,
        description=(
            "If true, exclusively lock returned records via Redis "
            "to prevent concurrent assignment to other users"
        ),
    )
    extration: bool | None = Field(
        None,
        description=(
            "If true, return records needing extraction: those without "
            "extracted text or with manual extraction and null segments. "
            "Deduplicated by file_hash (keeps earliest created_at)."
        ),
    )

    @field_validator("language")
    @classmethod
    def normalize_languages(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return [language.strip() for language in v]


class RecordReviewRequest(BaseModel):
    """Request schema for record review endpoint."""

    filters: RecordReviewFilters | None = Field(
        default_factory=RecordReviewFilters
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of record IDs to return (max 100)",
    )


class RecordReviewResponse(BaseModel):
    """Response schema for record review endpoint."""

    record_ids: list[dict] = Field(
        default_factory=list, description="List of record IDs for review"
    )


# Privacy utility functions
def filter_user_privacy(
    user_data: dict, requester_id: UUID, is_admin: bool = False
) -> dict:
    """Filter user data based on privacy settings and requester permissions."""
    from copy import deepcopy

    filtered_data = deepcopy(user_data)

    # Allow all fields if requester is admin or viewing their own profile
    if is_admin or user_data.get("id") == requester_id:
        return filtered_data

    # Apply privacy filtering for other users
    phone_privacy = user_data.get("phone_privacy", FieldPrivacy.private)
    email_privacy = user_data.get("email_privacy", FieldPrivacy.private)

    if phone_privacy == FieldPrivacy.private:
        filtered_data["phone"] = None

    if email_privacy == FieldPrivacy.private:
        filtered_data["email"] = None

    # Note: Place privacy filtering would go here if added later
    # For now, all place fields (current_place, from_place,
    # places_lived) are public

    return filtered_data


# Follow relationship schemas
class FollowersList(BaseModel):
    """List of users following a specific user."""

    user_id: UUID
    followers_count: int
    followers: list[UserRead]


class FollowingList(BaseModel):
    """List of users that a specific user is following."""

    user_id: UUID
    following_count: int
    following: list[UserRead]
