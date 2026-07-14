"""Tests for app/tasks/data_analysis.py.

These tests focus on testing the task functions without requiring
full Celery integration.
"""

from unittest.mock import MagicMock, Mock, patch


class TestPerformSpeechRecognition:
    """Tests for the perform_speech_recognition function."""

    def test_returns_placeholder_transcription(self):
        """Test that the function returns a placeholder transcription."""
        from app.tasks.data_analysis import perform_speech_recognition

        result = perform_speech_recognition("test_file.mp3")
        assert isinstance(result, str)
        assert len(result) > 0


class TestDetectLanguage:
    """Tests for the detect_language function."""

    def test_returns_telugu_for_text(self):
        """Test that language detection returns telugu for Indian text."""
        from app.tasks.data_analysis import detect_language

        result = detect_language("Telugu text content")
        assert "language" in result
        assert result["language"] == "te"
        assert "confidence" in result
        assert "alternatives" in result

    def test_alternatives_list_format(self):
        """Test that alternatives are properly formatted."""
        from app.tasks.data_analysis import detect_language

        result = detect_language("Sample text")
        assert isinstance(result["alternatives"], list)
        for alt in result["alternatives"]:
            assert "language" in alt
            assert "confidence" in alt


class TestAnalyzeAudioQuality:
    """Tests for the analyze_audio_quality function."""

    def test_returns_quality_metrics(self):
        """Test that quality analysis returns expected metrics."""
        from app.tasks.data_analysis import analyze_audio_quality

        result = analyze_audio_quality("test_file.mp3")
        assert "signal_to_noise_ratio" in result
        assert "peak_level" in result
        assert "rms_level" in result
        assert "quality_score" in result
        assert isinstance(result["quality_score"], float)
        assert 0 <= result["quality_score"] <= 1


class TestGenerateCorpusStatisticsTask:
    """Tests for the generate_corpus_statistics Celery task."""

    @patch("app.tasks.data_analysis.Session")
    @patch("app.tasks.data_analysis.engine")
    def test_generate_statistics_empty_database(
        self, mock_engine, mock_session
    ):
        """Test statistics generation with no records."""
        from app.tasks.data_analysis import generate_corpus_statistics

        mock_session_instance = MagicMock()
        mock_record = MagicMock()
        mock_record.media_type = Mock()
        mock_record.media_type.value = "audio"
        mock_record.status = "uploaded"
        mock_session_instance.exec.return_value.all.return_value = [mock_record]
        mock_session.return_value.__enter__ = Mock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__exit__ = Mock(return_value=False)

        result = generate_corpus_statistics()

        assert result["status"] == "success"
        assert "statistics" in result
        assert result["statistics"]["total_records"] >= 0

    @patch("app.tasks.data_analysis.Session")
    @patch("app.tasks.data_analysis.engine")
    def test_generate_statistics_with_user_filter(
        self, mock_engine, mock_session
    ):
        """Test statistics generation with user filter."""
        from app.tasks.data_analysis import generate_corpus_statistics

        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.all.return_value = []
        mock_session.return_value.__enter__ = Mock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__exit__ = Mock(return_value=False)

        user_id = 123
        result = generate_corpus_statistics(user_id=user_id)

        assert result["status"] == "success"
        assert result["user_id"] == user_id


class TestBatchLanguageDetectionTask:
    """Tests for the batch_language_detection Celery task."""

    @patch("app.tasks.data_analysis.Session")
    @patch("app.tasks.data_analysis.engine")
    def test_batch_language_detection_empty_list(
        self, mock_engine, mock_session
    ):
        """Test batch language detection with empty record list."""
        from app.tasks.data_analysis import batch_language_detection

        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__ = Mock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__exit__ = Mock(return_value=False)

        result = batch_language_detection([])

        assert result["total"] == 0
        assert len(result["processed"]) == 0
        assert len(result["failed"]) == 0

    @patch("app.tasks.data_analysis.Session")
    @patch("app.tasks.data_analysis.engine")
    def test_batch_language_detection_with_records(
        self, mock_engine, mock_session
    ):
        """Test batch language detection with some records."""
        from app.tasks.data_analysis import batch_language_detection

        mock_record = Mock()
        mock_record.uid = 1

        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = [mock_record, None]
        mock_session.return_value.__enter__ = Mock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__exit__ = Mock(return_value=False)

        result = batch_language_detection([1, 2])

        assert result["total"] == 2
        assert "processed" in result
        assert "failed" in result
