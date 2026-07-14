"""Tests for app/core/exceptions.py."""

from fastapi import status

from app.core.exceptions import (
    CategoryNotFound,
    CorpusException,
    DuplicateEntry,
    FileTooLarge,
    InvalidFileType,
    RecordNotFound,
    UserNotFound,
)


class TestCorpusException:
    """Test CorpusException base class."""

    def test_corpus_exception_default_status(self):
        """Test default status code is 400."""
        exc = CorpusException("Test error")
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.detail == "Test error"

    def test_corpus_exception_custom_status(self):
        """Test custom status code."""
        exc = CorpusException(
            "Test error", status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.detail == "Test error"

    def test_corpus_exception_is_http_exception(self):
        """Test it's an HTTPException."""
        exc = CorpusException("Test error")
        assert hasattr(exc, "status_code")
        assert hasattr(exc, "detail")


class TestUserNotFound:
    """Test UserNotFound exception."""

    def test_user_not_found_status_code(self):
        """Test status code is 404."""
        exc = UserNotFound("123")
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_user_not_found_message(self):
        """Test error message format."""
        exc = UserNotFound("123")
        assert "123" in exc.detail
        assert "User" in exc.detail
        assert "not found" in exc.detail


class TestCategoryNotFound:
    """Test CategoryNotFound exception."""

    def test_category_not_found_status_code(self):
        """Test status code is 404."""
        exc = CategoryNotFound("456")
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_category_not_found_message(self):
        """Test error message format."""
        exc = CategoryNotFound("456")
        assert "456" in exc.detail
        assert "Category" in exc.detail
        assert "not found" in exc.detail


class TestRecordNotFound:
    """Test RecordNotFound exception."""

    def test_record_not_found_status_code(self):
        """Test status code is 404."""
        exc = RecordNotFound("789")
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_record_not_found_message(self):
        """Test error message format."""
        exc = RecordNotFound("789")
        assert "789" in exc.detail
        assert "Record" in exc.detail
        assert "not found" in exc.detail


class TestDuplicateEntry:
    """Test DuplicateEntry exception."""

    def test_duplicate_entry_status_code(self):
        """Test status code is 409."""
        exc = DuplicateEntry("email", "test@example.com")
        assert exc.status_code == status.HTTP_409_CONFLICT

    def test_duplicate_entry_message(self):
        """Test error message format."""
        exc = DuplicateEntry("email", "test@example.com")
        assert "email" in exc.detail
        assert "test@example.com" in exc.detail
        assert "already exists" in exc.detail


class TestInvalidFileType:
    """Test InvalidFileType exception."""

    def test_invalid_file_type_status_code(self):
        """Test status code is 400."""
        exc = InvalidFileType("exe", ["jpg", "png"])
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_file_type_message(self):
        """Test error message format."""
        exc = InvalidFileType("exe", ["jpg", "png"])
        assert "exe" in exc.detail
        assert "jpg" in exc.detail
        assert "png" in exc.detail
        assert "not allowed" in exc.detail

    def test_invalid_file_type_with_multiple_allowed(self):
        """Test error message with multiple allowed types."""
        exc = InvalidFileType("pdf", ["jpg", "png", "gif", "mp3"])
        assert "pdf" in exc.detail
        assert "jpg, png, gif, mp3" in exc.detail


class TestFileTooLarge:
    """Test FileTooLarge exception."""

    def test_file_too_large_status_code(self):
        """Test status code is 413."""
        exc = FileTooLarge(1000000, 500000)
        assert exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_file_too_large_message(self):
        """Test error message format."""
        exc = FileTooLarge(1000000, 500000)
        assert "1000000" in exc.detail
        assert "500000" in exc.detail
        assert "exceeds" in exc.detail
        assert "bytes" in exc.detail

    def test_file_too_large_small_size(self):
        """Test with small file sizes."""
        exc = FileTooLarge(100, 50)
        assert "100" in exc.detail
        assert "50" in exc.detail
