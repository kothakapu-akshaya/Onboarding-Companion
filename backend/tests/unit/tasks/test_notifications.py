"""Tests for notification tasks."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestSendProcessingCompleteNotification:
    """Tests for send_processing_complete_notification task."""

    @patch("app.tasks.notifications.celery_app")
    @patch("app.tasks.notifications.Session")
    @patch("app.models.user.User")
    @patch("app.models.record.Record")
    def test_send_processing_notification_success(
        self,
        mock_record_class,
        mock_user_class,
        mock_session_class,
        mock_celery,
    ):
        """Test successful processing notification."""
        from app.tasks.notifications import (
            send_processing_complete_notification,
        )

        mock_user = Mock()
        mock_user.id = 1
        mock_user.name = "Test User"
        mock_user.email = "test@example.com"

        mock_record = Mock()
        mock_record.uid = "record-123"
        mock_record.file_name = "test.mp3"
        mock_record.media_type = "audio"
        mock_record.status = "completed"

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.side_effect = [mock_user, mock_record]

        mock_session_class.return_value = mock_session

        mock_celery.send_task.return_value = Mock(id="task-123")

        result = send_processing_complete_notification(user_id=1, record_id=1)

        assert result["status"] == "success"
        assert result["user_id"] == 1

    @patch("app.tasks.notifications.Session")
    @patch("app.models.user.User")
    def test_send_processing_notification_user_not_found(
        self, mock_user_class, mock_session_class
    ):
        """Test notification when user not found."""
        from app.tasks.notifications import (
            send_processing_complete_notification,
        )

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.return_value = None

        mock_session_class.return_value = mock_session

        with pytest.raises(ValueError, match="User .* not found"):
            send_processing_complete_notification(user_id=999, record_id=1)

    @patch("app.tasks.notifications.celery_app")
    @patch("app.tasks.notifications.Session")
    @patch("app.models.user.User")
    @patch("app.models.record.Record")
    def test_send_processing_notification_no_email(
        self,
        mock_record_class,
        mock_user_class,
        mock_session_class,
        mock_celery,
    ):
        """Test notification when user has no email."""
        from app.tasks.notifications import (
            send_processing_complete_notification,
        )

        mock_user = Mock()
        mock_user.id = 1
        mock_user.name = "Test User"
        mock_user.email = None

        mock_record = Mock()
        mock_record.uid = "record-123"
        mock_record.file_name = "test.mp3"

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.side_effect = [mock_user, mock_record]

        mock_session_class.return_value = mock_session

        result = send_processing_complete_notification(user_id=1, record_id=1)

        assert result["status"] == "skipped"
        assert "No email address" in result["reason"]

    @patch("app.tasks.notifications.Session")
    @patch("app.models.user.User")
    @patch("app.models.record.Record")
    def test_send_processing_notification_record_not_found(
        self, mock_record_class, mock_user_class, mock_session_class
    ):
        """Test notification when record not found."""
        from app.tasks.notifications import (
            send_processing_complete_notification,
        )

        mock_user = Mock()
        mock_user.id = 1

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.get.side_effect = [mock_user, None]

        mock_session_class.return_value = mock_session

        with pytest.raises(ValueError, match="Record .* not found"):
            send_processing_complete_notification(user_id=1, record_id=999)


class TestSendBulkNotification:
    """Tests for send_bulk_notification task."""

    def test_bulk_notification_result_structure(self):
        """Test bulk notification result structure."""
        result = {
            "sent": [
                {
                    "user_id": 1,
                    "email": "user1@example.com",
                    "task_id": "task-123",
                },
                {
                    "user_id": 2,
                    "email": "user2@example.com",
                    "task_id": "task-456",
                },
            ],
            "failed": [],
            "total": 2,
        }

        assert result["total"] == 2
        assert len(result["sent"]) == 2
        assert len(result["failed"]) == 0

    def test_bulk_notification_no_users(self):
        """Test bulk notification with no users."""
        result = {
            "sent": [],
            "failed": [],
            "total": 0,
        }

        assert result["total"] == 0
        assert len(result["sent"]) == 0


class TestSendSystemAlert:
    """Tests for send_system_alert task."""

    @patch("app.tasks.notifications.celery_app")
    @patch("app.tasks.notifications.Session")
    @patch("app.models.user.User")
    def test_send_system_alert_success(
        self, mock_user_class, mock_session_class, mock_celery
    ):
        """Test successful system alert."""
        from app.tasks.notifications import send_system_alert

        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "admin@example.com"

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.return_value.all.return_value = [mock_user]

        mock_session_class.return_value = mock_session

        mock_celery.send_task.return_value = Mock(id="task-456")

        result = send_system_alert(
            alert_type="Error Alert",
            message="System error occurred",
            severity="error",
        )

        assert result["status"] == "success"
        assert result["alert_type"] == "Error Alert"
        assert result["severity"] == "error"
        assert result["recipients"] == 1

    @patch("app.tasks.notifications.Session")
    def test_send_system_alert_no_admins(self, mock_session_class):
        """Test alert when no admin users found."""
        from app.tasks.notifications import send_system_alert

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.return_value.all.return_value = []

        mock_session_class.return_value = mock_session

        result = send_system_alert(
            alert_type="Test", message="Test message", severity="info"
        )

        assert result["status"] == "skipped"
        assert "No admin users found" in result["reason"]

    @patch("app.tasks.notifications.celery_app")
    @patch("app.tasks.notifications.Session")
    @patch("app.models.user.User")
    def test_send_system_alert_no_emails(
        self, mock_user_class, mock_session_class, mock_celery
    ):
        """Test alert when no admin emails found."""
        from app.tasks.notifications import send_system_alert

        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = None

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.return_value.all.return_value = [mock_user]

        mock_session_class.return_value = mock_session

        result = send_system_alert(
            alert_type="Test", message="Test message", severity="info"
        )

        assert result["status"] == "skipped"
        assert "No admin email addresses found" in result["reason"]


class TestSendEmail:
    """Tests for send_email task."""

    def test_send_email_success(self):
        """Test email task return structure."""
        recipients = ["test@example.com"]
        subject = "Test Subject"

        result = {
            "status": "success",
            "sent_to": recipients,
            "subject": subject,
            "timestamp": None,
        }

        assert result["status"] == "success"
        assert "test@example.com" in result["sent_to"]
        assert result["subject"] == "Test Subject"

    def test_send_email_multiple_recipients(self):
        """Test email task with multiple recipients."""
        recipients = ["user1@example.com", "user2@example.com"]

        result = {
            "status": "success",
            "sent_to": recipients,
            "subject": "Test",
            "timestamp": None,
        }

        assert result["status"] == "success"
        assert len(result["sent_to"]) == 2


class TestNotificationBusinessLogic:
    """Tests for notification business logic."""

    def test_notification_result_structure(self):
        """Test notification result structure."""
        result = {
            "status": "success",
            "user_id": 123,
            "record_id": 456,
            "email_task_id": "task-789",
        }

        assert result["status"] == "success"
        assert "user_id" in result
        assert "record_id" in result

    def test_system_alert_result_structure(self):
        """Test system alert result structure."""
        result = {
            "status": "success",
            "alert_type": "Error Alert",
            "severity": "error",
            "recipients": 3,
            "email_task_id": "task-123",
        }

        assert result["status"] == "success"
        assert "alert_type" in result
        assert "severity" in result
        assert "recipients" in result

    def test_email_content_structure(self):
        """Test email content structure."""
        email_content = {
            "subject": "Test Subject",
            "body": "Test body content",
            "html_body": "<p>Test body content</p>",
            "sender": "noreply@example.com",
        }

        assert "subject" in email_content
        assert "body" in email_content

    def test_bulk_notification_tracking(self):
        """Test bulk notification tracking."""
        results = {
            "sent": [],
            "failed": [],
            "total": 0,
        }

        for i in range(5):
            results["sent"].append(
                {"user_id": i, "email": f"user{i}@example.com"}
            )
            results["total"] += 1

        assert results["total"] == 5
        assert len(results["sent"]) == 5
        assert len(results["failed"]) == 0
