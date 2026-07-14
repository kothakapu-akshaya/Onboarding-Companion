"""Tests for backfill/file_integrity_check.py nullify_snr."""

from unittest.mock import MagicMock, patch

from backfill.file_integrity_check import nullify_snr


class TestNullifySnr:
    """Tests for nullify_snr function."""

    def test_sets_speech_not_detected_when_nullifying(self):
        """nullify_snr sets speech_not_detected=True with snr_frequency=NULL."""
        mock_record = MagicMock()
        mock_record.speech_not_detected = False
        mock_record.snr_frequency = 12.5

        mock_session = MagicMock()
        mock_session.get.return_value = mock_record
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        sess_path = "backfill.file_integrity_check.Session"
        with patch(sess_path, return_value=mock_session):
            nullify_snr("test-uid-123", dry_run=False)

        assert mock_record.speech_not_detected is True
        assert mock_record.snr_frequency is None
        mock_session.commit.assert_called_once()

    def test_dry_run_skips_db_write(self):
        """Dry run logs the intent and does not modify the record."""
        mock_session = MagicMock()
        mock_session.get.return_value = MagicMock()

        sess_path = "backfill.file_integrity_check.Session"
        with (
            patch(sess_path, return_value=mock_session),
            patch("backfill.file_integrity_check.logger") as mock_logger,
        ):
            nullify_snr("test-uid-123", dry_run=True)

        mock_session.commit.assert_not_called()
        mock_logger.info.assert_called_once()
        assert "speech_not_detected = True" in mock_logger.info.call_args[0][0]

    def test_skips_when_record_not_found(self):
        """Silently skips if the record UID no longer exists."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        sess_path = "backfill.file_integrity_check.Session"
        with patch(sess_path, return_value=mock_session):
            nullify_snr("missing-uid", dry_run=False)

        mock_session.commit.assert_not_called()
