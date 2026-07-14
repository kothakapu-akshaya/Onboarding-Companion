"""Tests for cleanup_storage utility functions."""

import sys
from unittest.mock import Mock, patch


class TestListAllObjects:
    """Tests for list_all_objects function."""

    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_list_all_objects_success(self, mock_get_client):
        """Test list all objects success."""
        from app.utils.cleanup_storage import list_all_objects

        mock_client = Mock()
        mock_client.list_objects.return_value = [
            {
                "object_key": "audio/test.mp3",
                "size": 1024 * 1024,
                "object_url": "https://example.com/bucket/audio/test.mp3",
                "last_modified": "2024-01-01T00:00:00",
            },
            {
                "object_key": "video/test.mp4",
                "size": 2 * 1024 * 1024,
                "object_url": "https://example.com/bucket/video/test.mp4",
                "last_modified": "2024-01-02T00:00:00",
            },
        ]
        mock_get_client.return_value = mock_client

        result = list_all_objects()

        assert len(result) == 2
        mock_client.list_objects.assert_called_once_with(
            prefix="", max_keys=10000
        )

    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_list_all_objects_empty(self, mock_get_client):
        """Test list all objects empty."""
        from app.utils.cleanup_storage import list_all_objects

        mock_client = Mock()
        mock_client.list_objects.return_value = []
        mock_get_client.return_value = mock_client

        result = list_all_objects()

        assert result == []

    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_list_all_objects_exception(self, mock_get_client):
        """Test list all objects exception."""
        from app.utils.cleanup_storage import list_all_objects

        mock_client = Mock()
        mock_client.list_objects.side_effect = Exception("Connection error")
        mock_get_client.return_value = mock_client

        result = list_all_objects()

        assert result == []


class TestDeleteAllObjects:
    """Tests for delete_all_objects function."""

    @patch("builtins.input", return_value="yes")
    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_delete_all_objects_success(self, mock_get_client, mock_input):
        """Test delete all objects success."""
        from app.utils.cleanup_storage import delete_all_objects

        mock_client = Mock()
        mock_client.list_objects.return_value = [
            {"object_key": "audio/test.mp3"},
        ]
        mock_client.delete_object.return_value = True
        mock_get_client.return_value = mock_client

        delete_all_objects(force=False)

        mock_client.delete_object.assert_called_once_with("audio/test.mp3")

    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_delete_all_objects_force(self, mock_get_client):
        """Test delete all objects force."""
        from app.utils.cleanup_storage import delete_all_objects

        mock_client = Mock()
        mock_client.list_objects.return_value = [
            {"object_key": "audio/test.mp3"},
        ]
        mock_client.delete_object.return_value = True
        mock_get_client.return_value = mock_client

        delete_all_objects(force=True)

        mock_client.delete_object.assert_called_once_with("audio/test.mp3")

    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_delete_all_objects_empty(self, mock_get_client):
        """Test delete all objects empty."""
        from app.utils.cleanup_storage import delete_all_objects

        mock_client = Mock()
        mock_client.list_objects.return_value = []
        mock_get_client.return_value = mock_client

        delete_all_objects(force=True)

        mock_client.delete_object.assert_not_called()

    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_delete_all_objects_cancelled(self, mock_get_client):
        """Test delete all objects cancelled."""
        from app.utils.cleanup_storage import delete_all_objects

        mock_client = Mock()
        mock_client.list_objects.return_value = [
            {"object_key": "audio/test.mp3"},
        ]
        mock_get_client.return_value = mock_client

        with patch("builtins.input", return_value="no"):
            delete_all_objects(force=False)

        mock_client.delete_object.assert_not_called()

    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_delete_all_objects_delete_failure(self, mock_get_client):
        """Test delete all objects delete failure."""
        from app.utils.cleanup_storage import delete_all_objects

        mock_client = Mock()
        mock_client.list_objects.return_value = [
            {"object_key": "audio/test.mp3"},
        ]
        mock_client.delete_object.return_value = False
        mock_get_client.return_value = mock_client

        delete_all_objects(force=True)

        mock_client.delete_object.assert_called_once()

    @patch("app.utils.cleanup_storage.get_storage_client")
    def test_delete_all_objects_exception(self, mock_get_client):
        """Test delete all objects exception."""
        from app.utils.cleanup_storage import delete_all_objects

        mock_client = Mock()
        mock_client.list_objects.side_effect = Exception("Connection error")
        mock_get_client.return_value = mock_client

        delete_all_objects(force=True)


class TestMain:
    """Tests for main function."""

    @patch("app.utils.cleanup_storage.list_all_objects")
    def test_main_list_command(self, mock_list):
        """Test main list command."""
        from app.utils.cleanup_storage import main

        mock_list.return_value = []

        sys.argv = ["cleanup_storage.py", "list"]
        main()

        mock_list.assert_called_once()

    @patch("app.utils.cleanup_storage.delete_all_objects")
    def test_main_delete_command(self, mock_delete):
        """Test main delete command."""
        from app.utils.cleanup_storage import main

        mock_delete.return_value = None

        sys.argv = ["cleanup_storage.py", "delete"]
        main()

        mock_delete.assert_called_once_with(force=False)

    @patch("app.utils.cleanup_storage.delete_all_objects")
    def test_main_delete_force_command(self, mock_delete):
        """Test main delete force command."""
        from app.utils.cleanup_storage import main

        mock_delete.return_value = None

        sys.argv = ["cleanup_storage.py", "delete", "--force"]
        main()

        mock_delete.assert_called_once_with(force=True)

    @patch("builtins.print")
    def test_main_unknown_command(self, mock_print):
        """Test main unknown command."""
        from app.utils.cleanup_storage import main

        sys.argv = ["cleanup_storage.py", "unknown"]
        main()

        mock_print.assert_called()

    def test_main_no_arguments(self):
        """Test main no arguments."""
        from app.utils.cleanup_storage import main

        with patch("builtins.print") as mock_print:
            sys.argv = ["cleanup_storage.py"]
            main()
            mock_print.assert_called()
