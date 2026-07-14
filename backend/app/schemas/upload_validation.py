"""Upload and content submission validation schemas.

Handles file uploads, content validation, and media-specific requirements.
"""

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

if TYPE_CHECKING:
    from app.schemas import MediaType, ReleaseRights
else:
    # At runtime, use string enums to avoid circular import
    from enum import Enum

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


from app.core.validators import (
    validate_content_description,
    validate_content_title,
    validate_coordinates,
    validate_file_size,
)
from app.schemas.geo_schemas import Coordinates


class ContentValidationBase(BaseModel):
    """Base validation for all content submissions."""

    title: str = Field(
        ..., min_length=8, max_length=200, description="Content title"
    )
    description: str = Field(
        ..., min_length=16, max_length=2000, description="Content description"
    )
    language: str = Field(..., description="Content language")
    release_rights: ReleaseRights = Field(
        ..., description="Release rights declaration"
    )
    location: Coordinates = Field(..., description="Geographic location")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Enhanced title validation."""
        validated = validate_content_title(v)
        word_count = len(validated.split())
        if word_count < 2:
            raise ValueError("Title should contain at least 2 meaningful words")
        return validated

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Enhanced description validation."""
        return validate_content_description(v)

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        return v.strip()

    @field_validator("release_rights")
    @classmethod
    def validate_release_rights(cls, v: ReleaseRights) -> ReleaseRights:
        """Validate release rights selection."""
        if v == ReleaseRights.NA:
            raise ValueError(
                "Release rights must be declared. Please select whether this "
                "content is created by you or with permission from "
                "family/friends."
            )

        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: Coordinates) -> Coordinates:
        """Enhanced location validation."""
        lat, lng = validate_coordinates(v.latitude, v.longitude)
        return Coordinates(latitude=lat, longitude=lng)


class FileUploadValidation(BaseModel):
    """Base file upload validation."""

    file_name: str = Field(
        ..., max_length=255, description="Original file name"
    )
    file_type: str = Field(..., description="MIME type of the file")
    file_size_bytes: int = Field(..., ge=1, description="File size in bytes")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Validate file name."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("File name is required")

        # Check for suspicious file extensions
        dangerous_extensions = [
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".pif",
            ".scr",
            ".vbs",
            ".js",
        ]
        if any(cleaned.lower().endswith(ext) for ext in dangerous_extensions):
            raise ValueError("File type not allowed for security reasons")

        return cleaned

    @field_validator("file_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        """Validate MIME type."""
        if not v.strip():
            raise ValueError("File type is required")

        # Basic MIME type format validation
        if "/" not in v:
            raise ValueError("Invalid file type format")

        return v.strip().lower()


class AudioFileValidation(FileUploadValidation):
    """Audio file validation."""

    duration_seconds: float | None = Field(
        None, description="Audio duration in seconds"
    )
    sample_rate: int | None = Field(None, description="Audio sample rate")
    channels: int | None = Field(None, description="Number of audio channels")

    @field_validator("file_type")
    @classmethod
    def validate_audio_format(cls, v: str) -> str:
        """Validate audio file format."""
        valid_formats = {
            "audio/wav",
            "audio/mp3",
            "audio/mpeg",
            "audio/ogg",
            "audio/webm",
            "audio/flac",
        }
        cleaned = v.strip().lower()
        if cleaned not in valid_formats:
            raise ValueError(
                f"Unsupported audio format: {v}. "
                f"Supported formats: {', '.join(valid_formats)}"
            )
        return cleaned

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate audio file size."""
        max_size = 500 * 1024 * 1024  # 500MB
        return validate_file_size(v, max_size)

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: float | None) -> float | None:
        """Validate audio duration."""
        if v is not None:
            if v < 5:  # 5 seconds minimum
                raise ValueError("Audio duration must be at least 5 seconds")
            if v > 900:  # 15 minutes maximum
                raise ValueError(
                    "Audio duration must not exceed 15 minutes (900 seconds)"
                )
            if v <= 0:
                raise ValueError("Invalid audio duration")
        return v

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int | None) -> int | None:
        """Validate audio sample rate."""
        if v is not None:
            if v < 8000:  # Minimum sample rate
                raise ValueError("Audio sample rate too low (minimum 8000 Hz)")
            if v > 192000:  # Maximum reasonable sample rate
                raise ValueError(
                    "Audio sample rate too high (maximum 192000 Hz)"
                )
        return v

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: int | None) -> int | None:
        """Validate number of audio channels."""
        if v is not None:
            if v < 1:
                raise ValueError("Audio must have at least 1 channel")
            if v > 8:  # Reasonable maximum
                raise ValueError("Too many audio channels (maximum 8)")
        return v


class VideoFileValidation(FileUploadValidation):
    """Video file validation."""

    duration_seconds: float | None = Field(
        None, description="Video duration in seconds"
    )
    width: int | None = Field(None, description="Video width in pixels")
    height: int | None = Field(None, description="Video height in pixels")
    frame_rate: float | None = Field(None, description="Video frame rate")

    @field_validator("file_type")
    @classmethod
    def validate_video_format(cls, v: str) -> str:
        """Validate video file format."""
        valid_formats = {
            "video/mp4",
            "video/webm",
            "video/avi",
            "video/mov",
            "video/mkv",
        }
        cleaned = v.strip().lower()
        if cleaned not in valid_formats:
            raise ValueError(
                f"Unsupported video format: {v}. "
                f"Supported formats: {', '.join(valid_formats)}"
            )
        return cleaned

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate video file size."""
        max_size = 2 * 1024 * 1024 * 1024  # 2GB
        return validate_file_size(v, max_size)

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: float | None) -> float | None:
        """Validate video duration."""
        if v is not None:
            if v < 1:  # 1 second minimum
                raise ValueError("Video duration must be at least 1 second")
            if v > 3600:  # 1 hour maximum
                raise ValueError(
                    "Video duration must not exceed 1 hour (3600 seconds)"
                )
        return v

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int | None) -> int | None:
        """Validate video dimensions."""
        if v is not None:
            if v < 1:
                raise ValueError("Invalid video dimensions")
            if v > 7680:  # 8K maximum
                raise ValueError(
                    "Video resolution too high (maximum 7680 pixels)"
                )
        return v

    @field_validator("frame_rate")
    @classmethod
    def validate_frame_rate(cls, v: float | None) -> float | None:
        """Validate video frame rate."""
        if v is not None:
            if v <= 0:
                raise ValueError("Invalid frame rate")
            if v > 120:  # 120fps maximum
                raise ValueError("Frame rate too high (maximum 120 fps)")
        return v


class ImageFileValidation(FileUploadValidation):
    """Image file validation."""

    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")

    @field_validator("file_type")
    @classmethod
    def validate_image_format(cls, v: str) -> str:
        """Validate image file format."""
        valid_formats = {
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/bmp",
            "image/webp",
        }
        cleaned = v.strip().lower()
        if cleaned not in valid_formats:
            raise ValueError(
                f"Unsupported image format: {v}. "
                f"Supported formats: {', '.join(valid_formats)}"
            )
        return cleaned

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate image file size."""
        max_size = 50 * 1024 * 1024  # 50MB
        return validate_file_size(v, max_size)

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int | None) -> int | None:
        """Validate image dimensions."""
        if v is not None:
            if v < 1:
                raise ValueError("Invalid image dimensions")
            if v > 16384:  # 16K maximum
                raise ValueError(
                    "Image resolution too high (maximum 16384 pixels)"
                )
        return v

    @model_validator(mode="after")
    def validate_image_aspect_ratio(self) -> "ImageFileValidation":
        """Validate image aspect ratio if dimensions are provided."""
        if self.width and self.height:
            aspect_ratio = self.width / self.height
            if aspect_ratio > 10 or aspect_ratio < 0.1:
                raise ValueError(
                    "Image aspect ratio is too extreme "
                    "(width:height should be between 1:10 and 10:1)"
                )
        return self


class TextFileValidation(FileUploadValidation):
    """Text file validation."""

    character_count: int | None = Field(
        None, description="Number of characters"
    )
    word_count: int | None = Field(None, description="Number of words")
    line_count: int | None = Field(None, description="Number of lines")

    @field_validator("file_type")
    @classmethod
    def validate_text_format(cls, v: str) -> str:
        """Validate text file format."""
        valid_formats = {
            "text/plain",
            "text/html",
            "text/markdown",
            "text/csv",
            "text/tab-separated-values",
        }
        cleaned = v.strip().lower()
        if cleaned not in valid_formats:
            raise ValueError(
                f"Unsupported text format: {v}. "
                f"Supported formats: {', '.join(valid_formats)}"
            )
        return cleaned

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate text file size."""
        max_size = 10 * 1024 * 1024  # 10MB
        return validate_file_size(v, max_size)

    @field_validator("character_count")
    @classmethod
    def validate_character_count(cls, v: int | None) -> int | None:
        """Validate text character count."""
        if v is not None:
            if v < 50:  # Minimum meaningful content
                raise ValueError(
                    "Text content must contain at least 50 characters"
                )
            if v > 10_000_000:  # 10M characters maximum
                raise ValueError(
                    "Text content is too long (maximum 10 million characters)"
                )
        return v

    @field_validator("word_count")
    @classmethod
    def validate_word_count(cls, v: int | None) -> int | None:
        """Validate text word count."""
        if v is not None:
            if v < 10:  # Minimum meaningful content
                raise ValueError(
                    "Text content should contain at least 10 words"
                )
        return v


class TextContentValidation(ContentValidationBase):
    """Validation for text content submissions."""

    media_type: MediaType = Field(
        default=MediaType.text, description="Media type"
    )
    text_content: str = Field(
        ..., min_length=50, max_length=1_000_000, description="Text content"
    )

    @field_validator("text_content")
    @classmethod
    def validate_text_content(cls, v: str) -> str:
        """Validate text content quality."""
        cleaned = v.strip()

        if len(cleaned) < 50:
            raise ValueError("Text content must be at least 50 characters long")

        # Check for reasonable word count
        word_count = len(cleaned.split())
        if word_count < 10:
            raise ValueError("Text content should contain at least 10 words")

        # Prevent spam or low-quality content
        unique_words = set(cleaned.lower().split())
        if len(unique_words) < 5:
            raise ValueError(
                "Text content appears repetitive. "
                "Please provide meaningful, varied content"
            )

        return cleaned


class AudioContentValidation(ContentValidationBase):
    """Validation for audio content submissions."""

    media_type: MediaType = Field(
        default=MediaType.audio, description="Media type"
    )
    audio_file: AudioFileValidation = Field(
        ..., description="Audio file information"
    )


class VideoContentValidation(ContentValidationBase):
    """Validation for video content submissions."""

    media_type: MediaType = Field(
        default=MediaType.video, description="Media type"
    )
    video_file: VideoFileValidation = Field(
        ..., description="Video file information"
    )


class ImageContentValidation(ContentValidationBase):
    """Validation for image content submissions."""

    media_type: MediaType = Field(
        default=MediaType.image, description="Media type"
    )
    image_file: ImageFileValidation = Field(
        ..., description="Image file information"
    )


class BatchUploadValidation(BaseModel):
    """Validation for batch upload requests."""

    uploads: list[dict[str, Any]] = Field(
        ..., min_length=1, max_length=50, description="List of uploads"
    )

    @field_validator("uploads")
    @classmethod
    def validate_upload_batch(
        cls, v: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate batch upload limits and format."""
        if len(v) > 50:
            raise ValueError("Batch upload limited to 50 items maximum")

        if not v:
            raise ValueError("Batch upload must contain at least 1 item")

        return v


class ChunkedUploadValidation(BaseModel):
    """Validation for chunked file upload."""

    chunk_number: int = Field(..., ge=1, description="Chunk sequence number")
    total_chunks: int = Field(..., ge=1, description="Total number of chunks")
    chunk_size: int = Field(..., ge=1, description="Size of this chunk")
    total_size: int = Field(..., ge=1, description="Total file size")
    upload_id: str = Field(
        ..., min_length=1, max_length=100, description="Upload session ID"
    )

    @model_validator(mode="after")
    def validate_chunk_consistency(self) -> "ChunkedUploadValidation":
        """Validate chunk upload consistency."""
        if self.chunk_number > self.total_chunks:
            raise ValueError("Chunk number cannot exceed total chunks")

        if self.chunk_size > self.total_size:
            raise ValueError("Chunk size cannot exceed total size")

        return self


# Helper functions for validation
def get_file_validator_by_type(media_type: MediaType):
    """Get appropriate file validator based on media type."""
    validators = {
        MediaType.audio: AudioFileValidation,
        MediaType.video: VideoFileValidation,
        MediaType.image: ImageFileValidation,
        MediaType.text: TextFileValidation,
    }
    return validators.get(media_type, FileUploadValidation)


def validate_file_extension_match(filename: str, mime_type: str) -> bool:
    """Validate that file extension matches MIME type."""
    extension_mime_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mp3",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".avi": "video/avi",
        ".mov": "video/mov",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".txt": "text/plain",
        ".html": "text/html",
        ".md": "text/markdown",
    }

    # Extract file extension
    if "." not in filename:
        return False

    ext = "." + filename.split(".")[-1].lower()
    expected_mime = extension_mime_map.get(ext)

    return expected_mime == mime_type.lower() if expected_mime else True


# New validation models for endpoints


class RecordUpdateValidation(BaseModel):
    """Enhanced Pydantic model for record updates.

    With advanced validation features.
    """

    title: str | None = Field(
        None,
        min_length=8,
        max_length=200,
        description="Record title",
        json_schema_extra={"example": "Traditional Folk Song from Kerala"},
    )
    description: str | None = Field(
        None,
        min_length=16,
        max_length=2000,
        description="Record description",
        json_schema_extra={
            "example": (
                "A beautiful traditional Malayalam folk "
                "song recorded during harvest season..."
            ),
        },
    )
    location: Coordinates | None = Field(
        None,
        description="Geographic location",
        json_schema_extra={
            "example": {"latitude": 10.8505, "longitude": 76.2711}
        },
    )
    release_rights: ReleaseRights | None = Field(
        None,
        description="Release rights declaration",
        json_schema_extra={"example": "created_by_user"},
    )
    language: str | None = Field(
        None,
        description="Content language",
        json_schema_extra={"example": "malayalam"},
    )
    published_date: date | None = Field(
        None,
        description="Published/event date of the record content",
        json_schema_extra={"example": "2024-01-15"},
    )
    creator: str | None = None
    source_label: str | None = Field(
        None, max_length=200, description="Label for the source of the record"
    )
    tagged_usernames: list[str] | None = Field(
        None, description="Usernames tagged in this record"
    )
    hashtags: list[str] | None = Field(
        None, description="Hashtags (without # prefix)"
    )
    record_tags: list[str] | None = Field(
        None, description="Admin-managed record tags"
    )
    source_url: HttpUrl | None = Field(
        None, description="URL for the source of the record"
    )
    speech_not_detected: bool | None = Field(
        None,
        description="Flag for corrupt audio/video with no usable audio track",
    )

    @field_validator("source_url")
    @classmethod
    def validate_source_url_length(cls, v: HttpUrl | None) -> HttpUrl | None:
        if v is not None and len(str(v)) > 500:
            raise ValueError("Source URL must not exceed 500 characters")
        return v

    @model_validator(mode="after")
    def validate_creator_for_others_release(self) -> "RecordUpdateValidation":
        """Validate that creator or source_label is provided.

        Required if release rights are 'others'.
        """
        # CORRECTED: Compare with the string value "others"
        if (
            self.release_rights == "others"
            and not self.creator
            and not self.source_label
        ):
            raise ValueError(
                "Either creator or source_label is required "
                "when release rights are 'others'."
            )
        return self

    # CORRECTED: The misplaced code is now a proper field_validator for 'title'
    @field_validator("title")
    @classmethod
    def validate_title_content(cls, v: str) -> str:
        """Validate title quality."""
        validated = validate_content_title(v)
        word_count = len(validated.split())
        if word_count < 2:
            raise ValueError("Title should contain at least 2 meaningful words")
        words = validated.lower().split()
        if len(set(words)) < len(words) * 0.5:
            raise ValueError(
                "Title appears to have excessive repetition. "
                "Please provide a more descriptive title"
            )
        return validated

    @field_validator("description")
    @classmethod
    def validate_description_content(cls, v: str | None) -> str | None:
        """Validate description quality."""
        if v is not None:
            validated = validate_content_description(v)
            word_count = len(validated.split())
            if word_count < 5:
                raise ValueError(
                    "Description should contain at least 5 "
                    "words for meaningful content"
                )
            if (
                validated.lower().count("http") > 0
                or validated.lower().count("www.") > 0
            ):
                raise ValueError("URLs are not allowed in descriptions")
            return validated
        return v

    @field_validator("location")
    @classmethod
    def validate_location_coords(
        cls, v: Coordinates | None
    ) -> Coordinates | None:
        """Enhanced location validation with geographic checks."""
        if v is not None:
            lat, lng = validate_coordinates(v.latitude, v.longitude)
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise ValueError("Invalid geographic coordinates")
            return Coordinates(latitude=lat, longitude=lng)
        return v

    @field_validator("published_date")
    @classmethod
    def validate_published_date(cls, v: date | None) -> date | None:
        """Validate the published/event date of the record content."""
        if v is None:
            return None
        today = date.today()
        if v > today:
            raise ValueError("Record date cannot be in the future")
        min_year = 1900
        if v.year < min_year:
            raise ValueError(f"Record date cannot be before year {min_year}")
        return v

    @field_validator("release_rights")
    @classmethod
    def validate_release_rights_selection(
        cls, v: ReleaseRights | None
    ) -> ReleaseRights | None:
        """Enhanced release rights validation with policy enforcement."""
        if v is not None:
            if v == "NA":
                raise ValueError(
                    "Release rights declaration is required. "
                    "Please specify the source of your content."
                )
        return v

    @field_validator("language")
    @classmethod
    def normalize_language(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip()

    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "title": "Traditional Malayalam Folk Song",
                "description": (
                    "A beautiful folk song passed down through generations..."
                ),
                "location": {"latitude": 10.8505, "longitude": 76.2711},
                "release_rights": "creator",
                "language": "ml",
            }
        }


class ChunkedUploadRequest(BaseModel):
    """Validation for chunked upload requests."""

    filename: str = Field(..., max_length=255, description="Original filename")
    chunk_index: int = Field(
        ..., ge=0, description="Current chunk index (0-based)"
    )
    total_chunks: int = Field(..., gt=0, description="Total number of chunks")
    upload_uuid: str = Field(..., description="Upload session UUID")

    @field_validator("filename")
    @classmethod
    def validate_filename_security(cls, v: str) -> str:
        """Validate filename for security."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Filename is required")

        # Check for path traversal attempts
        if ".." in cleaned or "/" in cleaned or "\\" in cleaned:
            raise ValueError("Filename contains invalid characters")

        # Check for dangerous extensions
        dangerous_extensions = [
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".pif",
            ".scr",
            ".vbs",
            ".js",
            ".jar",
        ]
        if any(cleaned.lower().endswith(ext) for ext in dangerous_extensions):
            raise ValueError("File type not allowed for security reasons")

        return cleaned

    @field_validator("upload_uuid")
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        """Validate UUID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("Invalid UUID format")

    @model_validator(mode="after")
    def validate_chunk_sequence(self) -> "ChunkedUploadRequest":
        """Validate chunk sequence consistency."""
        if self.chunk_index >= self.total_chunks:
            raise ValueError("Chunk index must be less than total chunks")
        return self


class UploadFinalizationRequest(BaseModel):
    """Validation for finalizing chunked uploads and creating records."""

    title: str = Field(
        ..., min_length=8, max_length=200, description="Record title"
    )
    description: str | None = Field(
        None, min_length=16, max_length=2000, description="Record description"
    )
    category_ids: str = Field(..., description="JSON array of category UUIDs")
    user_id: str = Field(..., description="User UUID")
    media_type: MediaType = Field(..., description="Media type")
    upload_uuid: str = Field(..., description="Upload session UUID")
    filename: str = Field(..., max_length=255, description="Original filename")
    total_chunks: int = Field(..., gt=0, description="Total number of chunks")
    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude")
    longitude: float | None = Field(
        None, ge=-180, le=180, description="Longitude"
    )
    release_rights: ReleaseRights = Field(..., description="Release rights")
    language: str = Field(..., description="Content language")
    use_uid_filename: bool = Field(
        False, description="Use record UID as filename"
    )
    creator: str | None = None
    source_label: str | None = Field(
        None, max_length=200, description="Label for the source of the record"
    )
    source_url: HttpUrl | None = Field(
        None, description="URL for the source of the record"
    )
    published_date: date | None = Field(
        None, description="Published date of the record"
    )
    tagged_usernames: str | None = Field(
        None, description="JSON array of username strings"
    )
    hashtags: str | None = Field(
        None, description="JSON array of hashtag strings"
    )
    record_tags: str | None = Field(
        None,
        description="JSON array of record tag UUIDs",
    )

    @field_validator("source_url")
    @classmethod
    def validate_source_url_length(cls, v: HttpUrl | None) -> HttpUrl | None:
        if v is not None and len(str(v)) > 500:
            raise ValueError("Source URL must not exceed 500 characters")
        return v

    @field_validator("title")
    @classmethod
    def validate_title_content(cls, v: str) -> str:
        """Validate title quality."""
        validated = validate_content_title(v)
        word_count = len(validated.split())
        if word_count < 2:
            raise ValueError("Title should contain at least 2 meaningful words")
        return validated

    @field_validator("description")
    @classmethod
    def validate_description_content(cls, v: str | None) -> str | None:
        """Validate description quality."""
        if v is not None:
            return validate_content_description(v)
        return v

    @field_validator("language")
    @classmethod
    def normalize_language(cls, v: str) -> str:
        return v.strip()

    # Only validate user_id and upload_uuid as single UUIDs
    @field_validator("user_id", "upload_uuid")
    @classmethod
    def validate_single_uuid_fields(cls, v: str) -> str:
        """Validate UUID format for single ID fields."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("Invalid UUID format")

    # Add a custom validator for category_ids JSON array
    @field_validator("category_ids")
    @classmethod
    def validate_category_ids_json(cls, v: str) -> str:
        """Validate that category_ids is a valid JSON array of UUID strings."""
        import json

        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError("category_ids must be a JSON array")
            for item in parsed:
                if not isinstance(item, str):
                    raise ValueError("Each category ID must be a string")
                uuid.UUID(item)  # Validate that each item is a valid UUID
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid category_ids JSON format: {str(e)}")
        return v

    @model_validator(mode="after")
    def validate_release_rights_requirements(
        self,
    ) -> "UploadFinalizationRequest":
        """Validate that creator or source_label is provided.

        Required if release rights are 'others'.
        """
        if (
            self.release_rights == "others"
            and not self.creator
            and not self.source_label
        ):
            raise ValueError(
                "Either creator or source_label is required "
                "when release rights are 'others'."
            )
        return self

    @model_validator(mode="after")
    def validate_location_consistency(self) -> "UploadFinalizationRequest":
        """Ensure both lat/lng are provided together."""
        has_lat = self.latitude is not None
        has_lng = self.longitude is not None

        if has_lat != has_lng:
            raise ValueError(
                "Both latitude and longitude must be "
                "provided together, or both omitted"
            )

        if has_lat and has_lng:
            # Validate coordinates using our validator
            latitude = self.latitude
            longitude = self.longitude
            if latitude is not None and longitude is not None:
                validate_coordinates(latitude, longitude)

        return self


class AudioValidationResult(BaseModel):
    """Result of audio file validation."""

    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information."""

    field: str
    message: str
    invalid_value: Any = None


class ValidationErrorResponse(BaseModel):
    """Standardized validation error response."""

    success: bool = False
    error_type: str = "validation_error"
    message: str
    errors: list[ValidationErrorDetail] = []
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
