"""Unit tests for the page count backfill helpers."""

import io
import zipfile
from unittest.mock import MagicMock, Mock, patch

from backfill.pages_count import (
    PageCountBackfiller,
    _count_docx_pages,
    get_document_page_count,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_docx_zip(pages_xml: str | None) -> str:
    """Write a minimal DOCX zip to a temp file and return the path."""
    import tempfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if pages_xml is not None:
            zf.writestr("docProps/app.xml", pages_xml)
    buf.seek(0)

    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    tmp.write(buf.read())
    tmp.close()
    return tmp.name


def _make_backfiller(**overrides) -> PageCountBackfiller:
    """Instantiate PageCountBackfiller without touching the DB or filesystem."""
    b = PageCountBackfiller.__new__(PageCountBackfiller)
    b.dry_run = overrides.get("dry_run", True)
    b.max_workers = 1
    b.batch_size = 10
    b.logger = MagicMock()
    return b


# ---------------------------------------------------------------------------
# get_document_page_count — routing layer
# ---------------------------------------------------------------------------


class TestGetDocumentPageCount:
    """Tests for get_document_page_count dispatch and safety wrapper."""

    def test_routes_pdf_to_pdf_helper(self):
        """Calls _count_pdf_pages for .pdf files and returns its result."""
        with patch(
            "backfill.pages_count._count_pdf_pages", return_value=5
        ) as mock_pdf:
            result = get_document_page_count("report.pdf")
        assert result == 5
        mock_pdf.assert_called_once_with("report.pdf")

    def test_routes_docx_to_docx_helper(self):
        """Calls _count_docx_pages for .docx files and returns its result."""
        with patch(
            "backfill.pages_count._count_docx_pages", return_value=3
        ) as mock_docx:
            result = get_document_page_count("doc.docx")
        assert result == 3
        mock_docx.assert_called_once_with("doc.docx")

    def test_unsupported_extension_returns_none(self):
        """Returns None and logs a warning for unrecognised extensions."""
        result = get_document_page_count("report.odt")
        assert result is None

    def test_extension_matching_is_case_insensitive(self):
        """Uppercase .PDF is handled the same as .pdf."""
        with patch("backfill.pages_count._count_pdf_pages", return_value=2):
            result = get_document_page_count("SCAN.PDF")
        assert result == 2

    def test_exception_from_pdf_helper_returns_none(self):
        """Outer safety handler catches any unexpected exception."""
        with patch(
            "backfill.pages_count._count_pdf_pages",
            side_effect=RuntimeError("boom"),
        ):
            result = get_document_page_count("test.pdf")
        assert result is None

    def test_exception_from_docx_helper_returns_none(self):
        """Outer safety handler catches any unexpected exception."""
        with patch(
            "backfill.pages_count._count_docx_pages",
            side_effect=RuntimeError("boom"),
        ):
            result = get_document_page_count("test.docx")
        assert result is None


# ---------------------------------------------------------------------------
# _count_pdf_pages — via sys.modules patching for the lazy import
# ---------------------------------------------------------------------------


class TestCountPdfPages:
    """Tests for _count_pdf_pages via the pypdf lazy-import path."""

    def _call(self, mock_reader_or_error):
        """Patch pypdf at import time and call _count_pdf_pages."""
        import sys

        from backfill.pages_count import _count_pdf_pages

        pypdf_mod = MagicMock()
        errors_mod = MagicMock()
        errors_mod.PdfReadError = type("PdfReadError", (Exception,), {})

        if isinstance(mock_reader_or_error, Exception):
            pypdf_mod.PdfReader = Mock(side_effect=mock_reader_or_error)
        else:
            pypdf_mod.PdfReader = Mock(return_value=mock_reader_or_error)

        with patch.dict(
            sys.modules, {"pypdf": pypdf_mod, "pypdf.errors": errors_mod}
        ):
            return _count_pdf_pages("dummy.pdf")

    def test_returns_page_count(self):
        mock_reader = Mock()
        mock_reader.pages = [Mock(), Mock(), Mock()]
        assert self._call(mock_reader) == 3

    def test_returns_none_for_zero_pages(self):
        mock_reader = Mock()
        mock_reader.pages = []
        assert self._call(mock_reader) is None

    def test_returns_none_for_corrupt_pdf(self):
        import sys

        from backfill.pages_count import _count_pdf_pages

        pypdf_mod = MagicMock()
        PdfReadError = type("PdfReadError", (Exception,), {})
        errors_mod = MagicMock()
        errors_mod.PdfReadError = PdfReadError
        pypdf_mod.PdfReader = Mock(side_effect=PdfReadError("bad"))

        with patch.dict(
            sys.modules, {"pypdf": pypdf_mod, "pypdf.errors": errors_mod}
        ):
            result = _count_pdf_pages("corrupt.pdf")
        assert result is None


# ---------------------------------------------------------------------------
# _count_docx_pages — uses real zip files in temp dir
# ---------------------------------------------------------------------------


class TestCountDocxPages:
    """Tests for _count_docx_pages with real DOCX-like zip files."""

    def test_returns_page_count_from_app_xml(self):
        xml = (
            '<?xml version="1.0"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            "<Pages>7</Pages>"
            "</Properties>"
        )
        path = _make_docx_zip(xml)
        try:
            assert _count_docx_pages(path) == 7
        finally:
            import os

            os.unlink(path)

    def test_returns_none_when_app_xml_missing(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("word/document.xml", "<root/>")
        buf.seek(0)

        import tempfile

        tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        tmp.write(buf.read())
        tmp.close()
        try:
            assert _count_docx_pages(tmp.name) is None
        finally:
            import os

            os.unlink(tmp.name)

    def test_returns_none_when_pages_element_absent(self):
        xml = (
            '<?xml version="1.0"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            "<Words>1234</Words>"
            "</Properties>"
        )
        path = _make_docx_zip(xml)
        try:
            assert _count_docx_pages(path) is None
        finally:
            import os

            os.unlink(path)

    def test_returns_none_for_zero_pages(self):
        xml = (
            '<?xml version="1.0"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            "<Pages>0</Pages>"
            "</Properties>"
        )
        path = _make_docx_zip(xml)
        try:
            assert _count_docx_pages(path) is None
        finally:
            import os

            os.unlink(path)

    def test_returns_none_for_non_integer_pages(self):
        xml = (
            '<?xml version="1.0"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            "<Pages>abc</Pages>"
            "</Properties>"
        )
        path = _make_docx_zip(xml)
        try:
            assert _count_docx_pages(path) is None
        finally:
            import os

            os.unlink(path)


# ---------------------------------------------------------------------------
# PageCountBackfiller.is_valid_result
# ---------------------------------------------------------------------------


class TestIsValidResult:
    """Tests for PageCountBackfiller.is_valid_result."""

    def test_valid_positive_count(self):
        assert _make_backfiller().is_valid_result(5, Mock()) is True

    def test_none_is_invalid(self):
        assert _make_backfiller().is_valid_result(None, Mock()) is False

    def test_zero_is_invalid(self):
        assert _make_backfiller().is_valid_result(0, Mock()) is False

    def test_negative_is_invalid(self):
        assert _make_backfiller().is_valid_result(-1, Mock()) is False


# ---------------------------------------------------------------------------
# PageCountBackfiller.update_records_batch
# ---------------------------------------------------------------------------


class TestUpdateRecordsBatch:
    """Tests for PageCountBackfiller.update_records_batch."""

    def test_empty_updates_returns_zero(self):
        assert _make_backfiller().update_records_batch([]) == 0

    def test_dry_run_skips_commit(self):
        """Dry-run counts records but never calls commit."""
        b = _make_backfiller(dry_run=True)
        mock_record = Mock()
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = mock_record

        with patch("backfill.pages_count.Session", return_value=mock_session):
            count = b.update_records_batch([("uid-1", 12), ("uid-2", 5)])

        assert count == 2
        mock_session.commit.assert_not_called()

    def test_skips_none_page_count(self):
        """Entries with None page_count are skipped."""
        b = _make_backfiller(dry_run=True)
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)

        with patch("backfill.pages_count.Session", return_value=mock_session):
            count = b.update_records_batch([("uid-1", None)])

        assert count == 0

    def test_live_run_commits_and_sets_field(self):
        """Live run writes page_count and calls commit."""
        b = _make_backfiller(dry_run=False)
        mock_record = Mock()
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = mock_record

        with patch("backfill.pages_count.Session", return_value=mock_session):
            count = b.update_records_batch([("uid-1", 3)])

        assert count == 1
        assert mock_record.page_count == 3
        mock_session.commit.assert_called_once()

    def test_missing_record_is_skipped(self):
        """Warns and skips when a UID no longer exists in the DB."""
        b = _make_backfiller(dry_run=False)
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = None  # record not found

        with patch("backfill.pages_count.Session", return_value=mock_session):
            count = b.update_records_batch([("uid-missing", 5)])

        assert count == 0
