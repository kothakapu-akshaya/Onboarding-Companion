"""Tests for RecordFileGenerator utility functions."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestRecordFileGenerator:
    """Tests for RecordFileGenerator class."""

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_init(self, mock_get_client):
        """Test init."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        generator = RecordFileGenerator()

        assert generator.storage_client == mock_client

    def test_generate_sample_content_text(self):
        """Test generate sample content text."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        with patch("app.utils.record_file_generator.get_storage_client"):
            generator = RecordFileGenerator()
            content = generator.generate_sample_content(
                MediaType.text, file_size_kb=1
            )

            assert len(content) <= 1024
            assert b"This is sample Indic languages" in content

    def test_generate_sample_content_audio(self):
        """Test generate sample content audio."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        with patch("app.utils.record_file_generator.get_storage_client"):
            generator = RecordFileGenerator()
            content = generator.generate_sample_content(
                MediaType.audio, file_size_kb=1
            )

            assert len(content) <= 1024
            assert content[:4] == b"\xff\xfb\x90\x00"

    def test_generate_sample_content_video(self):
        """Test generate sample content video."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        with patch("app.utils.record_file_generator.get_storage_client"):
            generator = RecordFileGenerator()
            content = generator.generate_sample_content(
                MediaType.video, file_size_kb=1
            )

            assert len(content) <= 1024
            assert content[:8] == b"\x00\x00\x00\x20\x66\x74\x79\x70"

    def test_generate_sample_content_image(self):
        """Test generate sample content image."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        with patch("app.utils.record_file_generator.get_storage_client"):
            generator = RecordFileGenerator()
            content = generator.generate_sample_content(
                MediaType.image, file_size_kb=1
            )

            assert len(content) <= 1024
            assert content[:10] == b"\xff\xd8\xff\xe0\x00\x10JFIF"

    def test_generate_sample_content_document(self):
        """Test generate sample content document."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        with patch("app.utils.record_file_generator.get_storage_client"):
            generator = RecordFileGenerator()
            content = generator.generate_sample_content(
                MediaType.document, file_size_kb=1
            )

            assert len(content) <= 1024
            assert b"%PDF-1.4" in content

    def test_get_file_extension(self):
        """Test get file extension."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        with patch("app.utils.record_file_generator.get_storage_client"):
            generator = RecordFileGenerator()

            assert generator.get_file_extension(MediaType.text) == ".txt"
            assert generator.get_file_extension(MediaType.audio) == ".mp3"
            assert generator.get_file_extension(MediaType.video) == ".mp4"
            assert generator.get_file_extension(MediaType.image) == ".jpg"
            assert generator.get_file_extension(MediaType.document) == ".pdf"

    def test_generate_filename_from_uid(self):
        """Test generate filename from uid."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        with patch("app.utils.record_file_generator.get_storage_client"):
            generator = RecordFileGenerator()
            record_uid = uuid4()
            filename = generator.generate_filename_from_uid(
                record_uid, MediaType.audio
            )

            assert str(record_uid) in filename
            assert filename.endswith(".mp3")


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch("app.utils.record_file_generator.RecordFileGenerator")
    def test_auto_generate_files_for_pending_records_success(
        self, mock_generator_class
    ):
        """Test auto generate files for pending records success."""
        from app.utils.record_file_generator import (
            auto_generate_files_for_pending_records,
        )

        mock_generator = Mock()
        mock_generator.get_records_without_files = Mock(
            return_value=[uuid4(), uuid4()]
        )
        mock_generator.bulk_process_records = AsyncMock(
            return_value=[
                {"success": True},
                {"success": True},
            ]
        )
        mock_generator_class.return_value = mock_generator

        result = asyncio.run(
            auto_generate_files_for_pending_records(limit=10, file_size_kb=1)
        )

        assert result["successful"] == 2
        assert result["failed"] == 0

    @patch("app.utils.record_file_generator.RecordFileGenerator")
    def test_auto_generate_files_for_pending_records_no_records(
        self, mock_generator_class
    ):
        """Test auto generate files for pending records no records."""
        from app.utils.record_file_generator import (
            auto_generate_files_for_pending_records,
        )

        mock_generator = Mock()
        mock_generator.get_records_without_files = Mock(return_value=[])
        mock_generator_class.return_value = mock_generator

        result = asyncio.run(
            auto_generate_files_for_pending_records(limit=10, file_size_kb=1)
        )

        assert result["processed"] == 0
        assert "No records without files found" in result["message"]


class TestRecordFileGeneratorAsyncMethods:
    """Tests for async methods in RecordFileGenerator."""

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_generate_sample_content_binary(self, mock_get_client):
        """Test generate sample content binary."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        generator = RecordFileGenerator()
        generator.generate_sample_content(
            "unknown" if hasattr(MediaType, "unknown") else MediaType.audio,
            file_size_kb=1,
        )

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_generate_sample_content_with_custom_type(self, mock_get_client):
        """Test generate sample content with custom type."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        generator = RecordFileGenerator()
        content = generator.generate_sample_content(
            MediaType.audio, file_size_kb=1
        )
        assert len(content) <= 1024
        assert content[:4] == b"\xff\xfb\x90\x00"

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_generate_sample_content_text_large(self, mock_get_client):
        """Test generate sample content text large."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        mock_client = Mock()
        mock_get_client.return_value = mock_client

        generator = RecordFileGenerator()
        content = generator.generate_sample_content(
            MediaType.text, file_size_kb=10
        )
        assert len(content) <= 10 * 1024
        assert b"This is sample Indic languages" in content


class TestCreateAndUploadFileForRecord:
    """Tests for create_and_upload_file_for_record method."""

    @patch("app.utils.record_file_generator.get_storage_client")
    @patch("app.utils.record_file_generator.datetime")
    def test_create_and_upload_file_success(
        self, mock_datetime, mock_get_client
    ):
        """Test create and upload file success."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        mock_datetime.now.return_value.isoformat.return_value = (
            "2024-01-01T00:00:00"
        )

        mock_client = Mock()
        mock_client.upload_file_data.return_value = {
            "object_key": "audio/test.mp3",
            "object_url": "https://example.com/audio/test.mp3",
            "file_size": 1024,
        }
        mock_get_client.return_value = mock_client

        generator = RecordFileGenerator()
        record_uid = uuid4()

        result = asyncio.run(
            generator.create_and_upload_file_for_record(
                record_uid=record_uid,
                media_type=MediaType.audio,
                file_size_kb=1,
                custom_metadata={"custom_key": "custom_value"},
            )
        )

        assert result["object_key"] == "audio/test.mp3"
        assert result["file_size"] == 1024
        mock_client.upload_file_data.assert_called_once()

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_create_and_upload_file_exception(self, mock_get_client):
        """Test create and upload file exception."""
        from app.utils.record_file_generator import (
            MediaType,
            RecordFileGenerator,
        )

        mock_client = Mock()
        mock_client.upload_file_data.side_effect = Exception("Upload failed")
        mock_get_client.return_value = mock_client

        generator = RecordFileGenerator()
        record_uid = uuid4()

        with pytest.raises(Exception, match="Upload failed"):
            asyncio.run(
                generator.create_and_upload_file_for_record(
                    record_uid=record_uid,
                    media_type=MediaType.audio,
                    file_size_kb=1,
                )
            )


class TestUpdateRecordWithFileInfo:
    """Tests for update_record_with_file_info method."""

    @patch("app.utils.record_file_generator.get_storage_client")
    @patch("app.utils.record_file_generator.datetime")
    def test_update_record_success(self, mock_datetime, mock_get_client):
        """Test update record success."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_datetime.now.return_value = "2024-01-01T00:00:00"

        mock_get_client.return_value = Mock()

        mock_record = Mock()
        mock_record.uid = uuid4()
        mock_record.file_url = None
        mock_record.file_name = None
        mock_record.file_size = None
        mock_record.status = None

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = mock_record

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            generator = RecordFileGenerator()
            record_uid = uuid4()
            upload_result = {
                "object_url": "https://example.com/audio/test.mp3",
                "object_key": "audio/test.mp3",
                "file_size": 1024,
            }

            result = asyncio.run(
                generator.update_record_with_file_info(
                    record_uid, upload_result
                )
            )

            assert result is True
            mock_session.add.assert_called_once_with(mock_record)
            mock_session.commit.assert_called_once()

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_update_record_not_found(self, mock_get_client):
        """Test update record not found."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = None

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            generator = RecordFileGenerator()
            record_uid = uuid4()
            upload_result = {
                "object_url": "https://example.com/audio/test.mp3",
                "object_key": "audio/test.mp3",
                "file_size": 1024,
            }

            result = asyncio.run(
                generator.update_record_with_file_info(
                    record_uid, upload_result
                )
            )

            assert result is False

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_update_record_exception(self, mock_get_client):
        """Test update record exception."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.side_effect = Exception("Database error")

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            generator = RecordFileGenerator()
            record_uid = uuid4()
            upload_result = {
                "object_url": "https://example.com/audio/test.mp3",
                "object_key": "audio/test.mp3",
                "file_size": 1024,
            }

            result = asyncio.run(
                generator.update_record_with_file_info(
                    record_uid, upload_result
                )
            )

            assert result is False


class TestProcessRecordWithFile:
    """Tests for process_record_with_file method."""

    @patch(
        "app.utils.record_file_generator.RecordFileGenerator.create_and_upload_file_for_record"
    )
    @patch(
        "app.utils.record_file_generator.RecordFileGenerator.update_record_with_file_info"
    )
    @patch("app.utils.record_file_generator.get_storage_client")
    def test_process_record_success(
        self,
        mock_get_client,
        mock_update_record,
        mock_upload_file,
    ):
        """Test process record success."""
        from app.models.record import MediaType
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_record = Mock()
        mock_record.media_type = MediaType.audio

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = mock_record

        mock_upload_file.return_value = {
            "object_key": "audio/test.mp3",
            "object_url": "https://example.com/audio/test.mp3",
            "file_size": 1024,
        }
        mock_update_record.return_value = True

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            generator = RecordFileGenerator()
            record_uid = uuid4()

            result = asyncio.run(
                generator.process_record_with_file(
                    record_uid=record_uid,
                    file_size_kb=1,
                    update_record=True,
                )
            )

            assert result["success"] is True
            assert result["record_updated"] is True

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_process_record_not_found(self, mock_get_client):
        """Test process record not found."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = None

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            generator = RecordFileGenerator()
            record_uid = uuid4()

            result = asyncio.run(
                generator.process_record_with_file(
                    record_uid=record_uid,
                    file_size_kb=1,
                    update_record=False,
                )
            )

            assert result["success"] is False
            assert "error" in result

    @patch(
        "app.utils.record_file_generator.RecordFileGenerator.create_and_upload_file_for_record"
    )
    @patch("app.utils.record_file_generator.get_storage_client")
    def test_process_record_upload_exception(
        self, mock_get_client, mock_upload_file
    ):
        """Test process record upload exception."""
        from app.models.record import MediaType
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_record = Mock()
        mock_record.media_type = MediaType.audio

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = mock_record

        mock_upload_file.side_effect = Exception("Upload failed")

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            generator = RecordFileGenerator()
            record_uid = uuid4()

            result = asyncio.run(
                generator.process_record_with_file(
                    record_uid=record_uid,
                    file_size_kb=1,
                    update_record=False,
                )
            )

            assert result["success"] is False
            assert "error" in result


class TestBulkProcessRecords:
    """Tests for bulk_process_records method."""

    @patch(
        "app.utils.record_file_generator.RecordFileGenerator.process_record_with_file"
    )
    @patch("app.utils.record_file_generator.get_storage_client")
    @patch(
        "app.utils.record_file_generator.asyncio.sleep", new_callable=AsyncMock
    )
    def test_bulk_process_success(
        self, mock_sleep, mock_get_client, mock_process
    ):
        """Test bulk process success."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_process.side_effect = [
            {"success": True},
            {"success": True},
        ]

        generator = RecordFileGenerator()
        record_uids = [uuid4(), uuid4()]

        results = asyncio.run(
            generator.bulk_process_records(
                record_uids=record_uids,
                file_size_kb=1,
                update_records=True,
            )
        )

        assert len(results) == 2
        assert all(r["success"] for r in results)

    @patch(
        "app.utils.record_file_generator.RecordFileGenerator.process_record_with_file"
    )
    @patch("app.utils.record_file_generator.get_storage_client")
    @patch(
        "app.utils.record_file_generator.asyncio.sleep", new_callable=AsyncMock
    )
    def test_bulk_process_with_failures(
        self, mock_sleep, mock_get_client, mock_process
    ):
        """Test bulk process with failures."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_process.side_effect = [
            {"success": True},
            Exception("Processing failed"),
        ]

        generator = RecordFileGenerator()
        record_uids = [uuid4(), uuid4()]

        results = asyncio.run(
            generator.bulk_process_records(
                record_uids=record_uids,
                file_size_kb=1,
                update_records=True,
            )
        )

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False


class TestGetRecordsWithoutFiles:
    """Tests for get_records_without_files method."""

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_get_records_without_files_success(self, mock_get_client):
        """Test get records without files success."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_record1 = Mock()
        mock_record1.uid = uuid4()
        mock_record1.file_url = None

        mock_record2 = Mock()
        mock_record2.uid = uuid4()
        mock_record2.file_url = "/files/local.txt"

        mock_record3 = Mock()
        mock_record3.uid = uuid4()
        mock_record3.file_url = "https://hetzner.storage/file.mp3"

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.return_value.all.return_value = [
            mock_record1,
            mock_record2,
            mock_record3,
        ]

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            with patch("app.utils.record_file_generator.select"):
                generator = RecordFileGenerator()
                result = generator.get_records_without_files(limit=10)

                assert len(result) == 2
                assert mock_record1.uid in result
                assert mock_record2.uid in result

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_get_records_without_files_empty(self, mock_get_client):
        """Test get records without files empty."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.return_value.all.return_value = []

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            with patch("app.utils.record_file_generator.select"):
                generator = RecordFileGenerator()
                result = generator.get_records_without_files(limit=10)

                assert len(result) == 0

    @patch("app.utils.record_file_generator.get_storage_client")
    def test_get_records_without_files_exception(self, mock_get_client):
        """Test get records without files exception."""
        from app.utils.record_file_generator import RecordFileGenerator

        mock_get_client.return_value = Mock()

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.side_effect = Exception("Database error")

        with patch(
            "app.utils.record_file_generator.Session", return_value=mock_session
        ):
            with patch("app.utils.record_file_generator.select"):
                generator = RecordFileGenerator()
                result = generator.get_records_without_files(limit=10)

                assert result == []


class TestMediaType:
    """Tests for MediaType enum."""

    def test_media_type_values(self):
        """Test media type values."""
        from app.models.record import MediaType

        assert MediaType.text.value == "text"
        assert MediaType.audio.value == "audio"
        assert MediaType.video.value == "video"
        assert MediaType.image.value == "image"
        assert MediaType.document.value == "document"
