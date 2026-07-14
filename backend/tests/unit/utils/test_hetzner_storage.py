"""Tests for Hetzner Storage utility functions."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestProgressLogs:
    """Tests for ProgressLogs class."""

    def test_progress_logs_init(self):
        """Test progress logs init."""
        from app.utils.hetzner_storage import ProgressLogs

        progress = ProgressLogs(filename="test.mp4")

        assert progress.filename == "test.mp4"
        assert progress.total_length == 0
        assert progress.current_size == 0

    def test_progress_logs_update(self):
        """Test progress logs update."""
        from app.utils.hetzner_storage import ProgressLogs

        progress = ProgressLogs(filename="test.mp4")
        progress.total_length = 100

        progress.update(50)

        assert progress.current_size == 50

    def test_progress_logs_update_invalid_type(self):
        """Test progress logs update invalid type."""
        from app.utils.hetzner_storage import ProgressLogs

        progress = ProgressLogs(filename="test.mp4")
        progress.total_length = 100

        with pytest.raises(ValueError, match="type cannot be displayed"):
            progress.update("invalid")

    def test_progress_logs_update_progress_logging(self):
        """Test progress logs update progress logging."""
        from app.utils.hetzner_storage import ProgressLogs

        progress = ProgressLogs(filename="test.mp4")
        progress.total_length = 100

        progress.update(10)
        progress.update(10)
        progress.update(10)
        progress.update(10)

        assert progress.current_size == 40

    def test_progress_logs_run(self):
        """Test progress logs run."""
        from app.utils.hetzner_storage import ProgressLogs

        progress = ProgressLogs(filename="test.mp4")
        progress.run()

        assert progress.daemon is True


class TestHetznerStorageClient:
    """Tests for HetznerStorageClient class."""

    def test_init_missing_credentials(self):
        """Test init missing credentials."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with patch("app.utils.hetzner_storage.settings") as mock_settings:
            mock_settings.MINIO_ENDPOINT = None
            mock_settings.MINIO_ACCESS_KEY = None
            mock_settings.MINIO_SECRET_KEY = None

            with pytest.raises(
                ValueError,
                match="Missing required Hetzner Object Storage credentials",
            ):
                HetznerStorageClient()

    def test_init_success(self):
        """Test init success."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()

            assert client.bucket_name == "test-bucket"

    def test_init_creates_bucket(self):
        """Test init creates bucket."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = False

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = False
            mock_minio.return_value = mock_client_instance

            HetznerStorageClient()

            mock_client_instance.make_bucket.assert_called_once_with(
                "test-bucket"
            )

    def test_init_endpoint_with_protocol(self):
        """Test init endpoint with protocol."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "https://s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            HetznerStorageClient()

            mock_minio.assert_called_once()
            call_args = mock_minio.call_args[0]
            assert call_args[0] == "s3.example.com"

    def test_generate_object_key(self):
        """Test generate object key."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()
            object_key = client.generate_object_key("test.mp4", "audio")

            assert object_key.startswith("audio/")
            assert object_key.endswith(".mp4")

    def test_generate_object_key_without_prefix(self):
        """Test generate object key without prefix."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()
            object_key = client.generate_object_key("test.mp4")

            assert not object_key.startswith("/")
            assert object_key.endswith(".mp4")

    def test_generate_object_key_prefix_without_slash(self):
        """Test generate object key prefix without slash."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()
            object_key = client.generate_object_key("test.mp4", "audio")

            assert object_key.startswith("audio/")

    def test_get_content_type(self):
        """Test get content type."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()

            content_type = client._get_content_type("test.mp3")
            assert content_type == "audio/mpeg"

    def test_get_content_type_unknown(self):
        """Test get content type unknown."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()

            content_type = client._get_content_type("test.unknown")
            assert content_type == "application/octet-stream"

    def test_get_object_url(self):
        """Test get object url."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True
            mock_settings.MINIO_PUBLIC_ENDPOINT = "https://example.com"

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()
            url = client.get_object_url("audio/test.mp3")

            assert "test-bucket" in url
            assert "audio/test.mp3" in url

    def test_get_presigned_url_get(self):
        """Test get presigned url get."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_client_instance.presigned_get_object.return_value = (
                "https://presigned.url"
            )
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()
            url = client.get_presigned_url(
                "audio/test.mp3", expires=timedelta(hours=1)
            )

            assert url == "https://presigned.url"
            mock_client_instance.presigned_get_object.assert_called_once()

    def test_get_presigned_url_put(self):
        """Test get presigned url put."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_client_instance.presigned_put_object.return_value = (
                "https://presigned.put.url"
            )
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()
            url = client.get_presigned_url("audio/test.mp3", method="PUT")

            assert url == "https://presigned.put.url"
            mock_client_instance.presigned_put_object.assert_called_once()

    def test_get_presigned_url_unsupported_method(self):
        """Test get presigned url unsupported method."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()

            with pytest.raises(ValueError, match="Unsupported method"):
                client.get_presigned_url("audio/test.mp3", method="DELETE")

    def test_delete_object_success(self):
        """Test delete object success."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True
            mock_minio.return_value = mock_client_instance

            client = HetznerStorageClient()
            result = client.delete_object("audio/test.mp3")

            assert result is True
            mock_client_instance.remove_object.assert_called_once()

    def test_list_objects_success(self):
        """Test list objects success."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
            patch(
                "app.utils.hetzner_storage.HetznerStorageClient.get_object_url"
            ) as mock_get_url,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True

            mock_obj1 = Mock()
            mock_obj1.object_name = "audio/test1.mp3"
            mock_obj1.size = 1024
            mock_obj1.etag = "etag1"
            mock_obj1.last_modified = datetime.now()
            mock_obj1.is_dir = False

            mock_obj2 = Mock()
            mock_obj2.object_name = "audio/test2.mp3"
            mock_obj2.size = 2048
            mock_obj2.etag = "etag2"
            mock_obj2.last_modified = datetime.now()
            mock_obj2.is_dir = False

            mock_client_instance.list_objects.return_value = [
                mock_obj1,
                mock_obj2,
            ]
            mock_minio.return_value = mock_client_instance
            mock_get_url.return_value = "https://example.com/bucket/path"

            client = HetznerStorageClient()
            result = client.list_objects(prefix="audio/")

            assert len(result) == 2
            assert result[0]["object_key"] == "audio/test1.mp3"

    def test_list_objects_with_max_keys(self):
        """Test list objects with max keys."""
        from app.utils.hetzner_storage import HetznerStorageClient

        with (
            patch("app.utils.hetzner_storage.Minio") as mock_minio,
            patch("app.utils.hetzner_storage.settings") as mock_settings,
            patch(
                "app.utils.hetzner_storage.HetznerStorageClient.get_object_url"
            ) as mock_get_url,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            mock_client_instance = Mock()
            mock_client_instance.bucket_exists.return_value = True

            mock_objs = []
            for i in range(5):
                mock_obj = Mock()
                mock_obj.object_name = f"audio/test{i}.mp3"
                mock_obj.size = 1024
                mock_obj.etag = f"etag{i}"
                mock_obj.last_modified = datetime.now()
                mock_obj.is_dir = False
                mock_objs.append(mock_obj)

            mock_client_instance.list_objects.return_value = mock_objs
            mock_minio.return_value = mock_client_instance
            mock_get_url.return_value = "https://example.com/bucket/path"

            client = HetznerStorageClient()
            result = client.list_objects(prefix="audio/", max_keys=3)

            assert len(result) == 3


class TestGetStorageClient:
    """Tests for get_storage_client function."""

    def test_get_storage_client_creates_new(self):
        """Test get storage client creates new."""
        from app.utils.hetzner_storage import (
            HetznerStorageClient,
            get_storage_client,
        )

        with (
            patch.object(HetznerStorageClient, "__init__", lambda self: None),
            patch("app.utils.hetzner_storage.settings") as mock_settings,
        ):
            mock_settings.MINIO_ENDPOINT = "s3.example.com"
            mock_settings.MINIO_ACCESS_KEY = "test_key"
            mock_settings.MINIO_SECRET_KEY = "test_secret"
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"
            mock_settings.MINIO_USE_SSL = True

            import app.utils.hetzner_storage as hetzner_module

            hetzner_module._storage_client = None

            mock_client_instance = Mock()
            with (
                patch("app.utils.hetzner_storage.Minio"),
                patch.object(
                    hetzner_module,
                    "HetznerStorageClient",
                    return_value=mock_client_instance,
                ),
            ):
                result = get_storage_client()

                assert result == mock_client_instance

    def test_get_storage_client_returns_existing(self):
        """Test get storage client returns existing."""
        from app.utils.hetzner_storage import get_storage_client

        mock_existing = Mock()

        import app.utils.hetzner_storage as hetzner_module

        hetzner_module._storage_client = mock_existing

        result = get_storage_client()

        assert result == mock_existing


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_upload_file_to_hetzner(self):
        """Test upload file to hetzner."""
        from app.utils.hetzner_storage import upload_file_to_hetzner

        mock_client = Mock()
        mock_client.upload_file = AsyncMock(return_value={"success": True})

        import app.utils.hetzner_storage as hetzner_module

        hetzner_module._storage_client = mock_client

        import asyncio

        result = asyncio.run(
            upload_file_to_hetzner("/tmp/test.mp4", prefix="audio")
        )

        assert result["success"] is True

    def test_get_file_url(self):
        """Test get file url."""
        from app.utils.hetzner_storage import get_file_url

        mock_client = Mock()
        mock_client.get_object_url.return_value = (
            "https://example.com/bucket/path"
        )

        import app.utils.hetzner_storage as hetzner_module

        hetzner_module._storage_client = mock_client

        result = get_file_url("audio/test.mp3", presigned=False)

        assert result == "https://example.com/bucket/path"

    def test_get_file_url_presigned(self):
        """Test get file url presigned."""
        from app.utils.hetzner_storage import get_file_url

        mock_client = Mock()
        mock_client.get_presigned_url.return_value = "https://presigned.url"

        import app.utils.hetzner_storage as hetzner_module

        hetzner_module._storage_client = mock_client

        result = get_file_url("audio/test.mp3", presigned=True, expires_hours=2)

        assert result == "https://presigned.url"


class TestGetObjectKeyFromUrl:
    """Tests for get_object_key_from_url function."""

    def test_get_object_key_from_url(self):
        """Test get object key from url."""
        from app.utils.hetzner_storage import get_object_key_from_url

        with patch("app.utils.hetzner_storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"

            result = get_object_key_from_url(
                "https://s3.example.com/test-bucket/audio/test.mp3",
                "test-bucket",
            )

            assert result == "audio/test.mp3"

    def test_get_object_key_from_url_no_match(self):
        """Test get object key from url no match."""
        from app.utils.hetzner_storage import get_object_key_from_url

        with patch("app.utils.hetzner_storage.settings") as mock_settings:
            mock_settings.MINIO_BUCKET_NAME = "test-bucket"

            result = get_object_key_from_url(
                "https://s3.example.com/other-bucket/audio/test.mp3",
                "test-bucket",
            )

            assert result is None

    def test_get_object_key_from_url_empty_url(self):
        """Test get object key from url empty url."""
        from app.utils.hetzner_storage import get_object_key_from_url

        result = get_object_key_from_url("", "test-bucket")

        assert result is None

    def test_get_object_key_from_url_none_url(self):
        """Test get object key from url none url."""
        from app.utils.hetzner_storage import get_object_key_from_url

        result = get_object_key_from_url(None, "test-bucket")

        assert result is None

    def test_get_object_key_from_url_empty_bucket(self):
        """Test get object key from url empty bucket."""
        from app.utils.hetzner_storage import get_object_key_from_url

        result = get_object_key_from_url("https://example.com/bucket/path", "")

        assert result is None

    def test_get_object_key_from_url_invalid_url(self):
        """Test get object key from url invalid url."""
        from app.utils.hetzner_storage import get_object_key_from_url

        result = get_object_key_from_url("not a valid url", "bucket")

        assert result is None
