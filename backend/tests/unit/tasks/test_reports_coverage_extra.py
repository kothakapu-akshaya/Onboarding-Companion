"""Extra coverage tests for report generation tasks."""

import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, mock_open, patch
from uuid import uuid4

import pytest

from app.tasks.reports import (
    export_user_data,
    generate_daily_report,
    generate_system_health_report,
    generate_user_report,
)


def result_all(rows):
    """Create a mock result object with all() returning rows."""
    result = Mock()
    result.all.return_value = rows
    return result


def result_first(value):
    """Create a mock result object with first() returning value."""
    result = Mock()
    result.first.return_value = value
    return result


def make_session(*exec_results, user=None):
    """Create a mock database session with configurable exec results."""
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False
    session.exec.side_effect = list(exec_results)
    session.get.return_value = user
    return session


def make_record(
    created_at,
    updated_at,
    status="completed",
    media_type=None,
    user_id=None,
    file_size=None,
):
    """Create a mock record SimpleNamespace with default values."""
    return SimpleNamespace(
        created_at=created_at,
        updated_at=updated_at,
        status=status,
        media_type=media_type,
        user_id=user_id or uuid4(),
        file_size=file_size,
        uid=uuid4(),
        title="Test Record",
        description="Test description",
        file_url="https://example.com/file.mp3",
        file_name="file.mp3",
        reviewed=False,
        reviewed_by=None,
        reviewed_at=None,
    )


def test_generate_daily_report_success_and_failure_paths():
    """Test generate_daily_report success and failure paths."""
    target_date = date(2024, 1, 15)
    new_record = make_record(
        datetime(2024, 1, 15, 10, 0),
        datetime(2024, 1, 15, 10, 0),
        status="completed",
        media_type=SimpleNamespace(value="audio"),
    )
    failed_record = make_record(
        datetime(2024, 1, 15, 11, 0),
        datetime(2024, 1, 15, 12, 0),
        status="failed",
        media_type=SimpleNamespace(value="video"),
    )
    processed_record = make_record(
        datetime(2024, 1, 15, 10, 0),
        datetime(2024, 1, 15, 13, 0),
        status="completed",
        media_type=SimpleNamespace(value="audio"),
    )

    session = make_session(
        result_all([new_record, failed_record, processed_record]),
        result_all([processed_record]),
        result_all([failed_record]),
    )

    with (
        patch("app.tasks.reports.Session", return_value=session),
        patch("app.tasks.reports.celery_app.send_task") as send_task,
    ):
        result = generate_daily_report.run(report_date=str(target_date))

    assert result["status"] == "success"
    assert result["report_data"]["summary"]["total_uploads"] == 3
    assert result["report_data"]["summary"]["total_processed"] == 1
    assert result["report_data"]["summary"]["total_failed"] == 1
    send_task.assert_called_once()

    failing_session = make_session(RuntimeError("db down"))
    failing_session.exec.side_effect = RuntimeError("db down")

    with (
        patch("app.tasks.reports.Session", return_value=failing_session),
        patch.object(generate_daily_report, "update_state") as update_state,
    ):
        with pytest.raises(RuntimeError):
            generate_daily_report.run(report_date=str(target_date))

    update_state.assert_called_once()


def test_generate_user_report_success_and_not_found():
    """Test generate_user_report success and user not found."""
    user_id = str(uuid4())
    user = SimpleNamespace(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
    )
    record = make_record(
        datetime(2024, 1, 15, 10, 0),
        datetime(2024, 1, 15, 10, 0),
        status="completed",
        media_type=SimpleNamespace(value="audio"),
        user_id=user.id,
    )
    session = make_session(result_all([record]), user=user)

    with patch("app.tasks.reports.Session", return_value=session):
        result = generate_user_report.run(user_id, "2024-01-01", "2024-01-31")

    assert result["status"] == "success"
    assert result["report_data"]["summary"]["total_uploads"] == 1
    assert result["report_data"]["summary"]["processed_count"] == 1

    missing_session = make_session(result_all([]), user=None)

    with (
        patch("app.tasks.reports.Session", return_value=missing_session),
        patch.object(generate_user_report, "update_state") as update_state,
    ):
        with pytest.raises(ValueError):
            generate_user_report.run(str(uuid4()))

    update_state.assert_called_once()


def test_generate_system_health_report_alerts_on_unhealthy_services():
    """Test that system health report alerts on unhealthy services."""
    db_health_session = make_session(Mock())
    stats_session = make_session(
        result_first(3),
        result_first(4),
        result_first(2),
        result_first(1),
        result_first(1),
        result_all(
            [
                make_record(
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc),
                    file_size=100,
                )
            ]
        ),
        result_all(
            [
                make_record(
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc),
                    file_size=100,
                )
            ]
        ),
    )
    fake_redis = SimpleNamespace(
        Redis=Mock(
            return_value=SimpleNamespace(
                ping=Mock(side_effect=RuntimeError("down"))
            )
        )
    )

    with (
        patch(
            "app.tasks.reports.Session",
            side_effect=[db_health_session, stats_session],
        ),
        patch("app.tasks.reports.celery_app.send_task") as send_task,
        patch.dict(sys.modules, {"redis": fake_redis}),
    ):
        result = generate_system_health_report.run()

    assert result["status"] == "success"
    assert result["report_data"]["database_stats"]["total_records"] == 4
    send_task.assert_called_once()


def test_export_user_data_success_and_unsupported_format():
    """Test export_user_data success and unsupported format."""
    user_id = str(uuid4())
    user = SimpleNamespace(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        phone="+919876543210",
        gender="male",
        date_of_birth=date(1990, 1, 1),
        place="Hyderabad",
        is_active=True,
        has_given_consent=True,
        last_login_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    record = make_record(
        datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        status="completed",
        media_type=SimpleNamespace(value="audio"),
        user_id=user.id,
    )
    session = make_session(result_all([record]), user=user)

    with (
        patch("app.tasks.reports.Session", return_value=session),
        patch("app.tasks.reports.open", mock_open()),
        patch("app.tasks.reports.os.path.getsize", return_value=1234),
    ):
        result = export_user_data.run(user_id, "json")

    assert result["status"] == "success"
    assert result["total_records"] == 1

    bad_session = make_session(result_all([record]), user=user)

    with (
        patch("app.tasks.reports.Session", return_value=bad_session),
        patch.object(export_user_data, "update_state") as update_state,
    ):
        with pytest.raises(ValueError):
            export_user_data.run(user_id, "csv")

    update_state.assert_called_once()
