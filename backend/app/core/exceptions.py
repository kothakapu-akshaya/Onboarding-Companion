"""Custom exception classes for the application."""

from fastapi import HTTPException, status


class CorpusException(HTTPException):
    """Base exception for corpus application."""

    def __init__(
        self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        """Initialize the CorpusException."""
        super().__init__(status_code=status_code, detail=detail)


class UserNotFound(CorpusException):
    """Exception raised when user is not found."""

    def __init__(self, user_id: str):
        """Initialize the UserNotFound."""
        super().__init__(
            detail=f"User with id {user_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class CategoryNotFound(CorpusException):
    """Exception raised when category is not found."""

    def __init__(self, category_id: str):
        """Initialize the CategoryNotFound."""
        super().__init__(
            detail=f"Category with id {category_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class RecordNotFound(CorpusException):
    """Exception raised when record is not found."""

    def __init__(self, record_id: str):
        """Initialize the RecordNotFound."""
        super().__init__(
            detail=f"Record with id {record_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DuplicateEntry(CorpusException):
    """Exception raised when trying to create a duplicate entry."""

    def __init__(self, field: str, value: str):
        """Initialize the DuplicateEntry."""
        super().__init__(
            detail=f"{field} '{value}' already exists",
            status_code=status.HTTP_409_CONFLICT,
        )


class InvalidFileType(CorpusException):
    """Exception raised when file type is not allowed."""

    def __init__(self, file_type: str, allowed_types: list[str]):
        """Initialize the InvalidFileType."""
        super().__init__(
            detail=(
                f"File type '{file_type}' not allowed. "
                f"Allowed types: {', '.join(allowed_types)}"
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class FileTooLarge(CorpusException):
    """Exception raised when file size exceeds limit."""

    def __init__(self, size: int, max_size: int):
        """Initialize the FileTooLarge."""
        super().__init__(
            detail=(
                f"File size {size} bytes exceeds maximum allowed size of "
                f"{max_size} bytes"
            ),
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
