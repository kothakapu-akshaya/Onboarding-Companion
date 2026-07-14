"""Tests for app/core/logging_config.py."""

from unittest.mock import MagicMock, patch


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_with_default_level(self):
        """Test setup_logging with default INFO level."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_log_dir = MagicMock()
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                setup_logging()

                mock_logging.basicConfig.assert_called_once()
                call_kwargs = mock_logging.basicConfig.call_args[1]
                assert call_kwargs["level"] == mock_logging.INFO

    def test_setup_logging_with_debug_level(self):
        """Test setup_logging with DEBUG level."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_log_dir = MagicMock()
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                setup_logging(level="DEBUG")

                mock_logging.basicConfig.assert_called_once()
                call_kwargs = mock_logging.basicConfig.call_args[1]
                assert call_kwargs["level"] == mock_logging.DEBUG

    def test_setup_logging_with_warning_level(self):
        """Test setup_logging with WARNING level."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_log_dir = MagicMock()
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                setup_logging(level="WARNING")

                mock_logging.basicConfig.assert_called_once()
                call_kwargs = mock_logging.basicConfig.call_args[1]
                assert call_kwargs["level"] == mock_logging.WARNING

    def test_tmp_directory_not_exists(self):
        """Test handling when /tmp doesn't exist."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_log_dir = MagicMock()
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                mock_logger = MagicMock()
                mock_logging.getLogger.return_value = mock_logger
                mock_logging.WARNING = 30

                setup_logging(level="WARNING")

    def test_tmp_write_permission_denied(self):
        """Test handling when /tmp write permission denied."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_tmp = MagicMock()
            mock_tmp.exists.return_value = True
            mock_tmp.__truediv__ = lambda self, x: MagicMock()
            mock_path.return_value = mock_tmp

            mock_test_file = MagicMock()
            mock_test_file.touch.side_effect = PermissionError("Access denied")
            mock_tmp.__truediv__.return_value = mock_test_file

            with patch("app.core.logging_config.logging") as mock_logging:
                mock_logger = MagicMock()
                mock_logging.getLogger.return_value = mock_logger
                mock_logging.WARNING = 30

                setup_logging(level="WARNING")

    def test_log_dir_exists_permission_denied(self):
        """Test handling when log_dir exists but has no write permission."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_tmp = MagicMock()
            mock_tmp.exists.return_value = True
            mock_path.return_value = mock_tmp

            mock_log_dir = MagicMock()
            mock_log_dir.exists.return_value = True
            mock_log_dir.__truediv__ = lambda self, x: MagicMock()

            mock_test_file = MagicMock()
            mock_test_file.touch.side_effect = PermissionError("Access denied")
            mock_log_dir.__truediv__.return_value = mock_test_file

            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                mock_logger = MagicMock()
                mock_logging.getLogger.return_value = mock_logger
                mock_logging.WARNING = 30

                setup_logging(level="WARNING")

    def test_log_dir_mkdir_permission_error(self):
        """Test handling when mkdir fails with PermissionError."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_tmp = MagicMock()
            mock_tmp.exists.return_value = True
            mock_path.return_value = mock_tmp

            mock_log_dir = MagicMock()
            mock_log_dir.exists.side_effect = [False, False, True]
            mock_log_dir.mkdir.side_effect = PermissionError(
                "Permission denied"
            )
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                mock_logger = MagicMock()
                mock_logging.getLogger.return_value = mock_logger
                mock_logging.WARNING = 30
                mock_logging.PERMISSIONERROR = 30

                setup_logging(level="WARNING")

    def test_log_dir_mkdir_os_error(self):
        """Test handling when mkdir fails with OSError."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_tmp = MagicMock()
            mock_tmp.exists.return_value = True
            mock_path.return_value = mock_tmp

            mock_log_dir = MagicMock()
            mock_log_dir.exists.side_effect = [False, False, True]
            mock_log_dir.mkdir.side_effect = OSError("OS error")
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                mock_logger = MagicMock()
                mock_logging.getLogger.return_value = mock_logger
                mock_logging.WARNING = 30
                mock_logging.OSERROR = 40

                setup_logging(level="WARNING")

    def test_log_dir_mkdir_unexpected_error(self):
        """Test handling when mkdir fails with unexpected error."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_tmp = MagicMock()
            mock_tmp.exists.return_value = True
            mock_path.return_value = mock_tmp

            mock_log_dir = MagicMock()
            mock_log_dir.exists.side_effect = [False, False, True]
            mock_log_dir.mkdir.side_effect = Exception("Unexpected error")
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                mock_logger = MagicMock()
                mock_logging.getLogger.return_value = mock_logger
                mock_logging.WARNING = 30

                setup_logging(level="WARNING")

    def test_sets_logger_levels(self):
        """Test that logger levels are set for common loggers."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_log_dir = MagicMock()
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                setup_logging()

                assert mock_logging.getLogger("uvicorn").setLevel.called
                assert mock_logging.getLogger("uvicorn.access").setLevel.called
                assert mock_logging.getLogger(
                    "sqlalchemy.engine"
                ).setLevel.called
                assert mock_logging.getLogger("watchfiles").setLevel.called
                assert mock_logging.getLogger("asyncio").setLevel.called
                assert mock_logging.getLogger("multipart").setLevel.called

    def test_stream_handler_added(self):
        """Test that StreamHandler is added to handlers."""
        from app.core.logging_config import setup_logging

        with patch("app.core.logging_config.Path") as mock_path:
            mock_log_dir = MagicMock()
            mock_path.return_value = mock_log_dir

            with patch("app.core.logging_config.logging") as mock_logging:
                setup_logging()

                call_kwargs = mock_logging.basicConfig.call_args[1]
                assert "handlers" in call_kwargs
                assert len(call_kwargs["handlers"]) > 0
