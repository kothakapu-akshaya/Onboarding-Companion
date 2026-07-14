"""Unit tests for app/schemas/task.py Pydantic models."""

import pytest
from pydantic import ValidationError

from app.schemas.task import (
    BatchProcessRequest,
    CleanupRequest,
    ExportRequest,
    NotificationRequest,
    ReportRequest,
    SystemAlertRequest,
    TaskInfo,
    TaskListResponse,
    TaskResponse,
    TaskStatusResponse,
)

# ============================================================
# TaskResponse
# ============================================================


class TestTaskResponse:
    """Tests for TaskResponse schema."""

    def test_create_with_valid_data(self):
        response = TaskResponse(
            task_id="task-123",
            task_name="Process Data",
            status="completed",
            message="Task finished successfully",
        )
        assert response.task_id == "task-123"
        assert response.task_name == "Process Data"
        assert response.status == "completed"
        assert response.message == "Task finished successfully"

    def test_missing_required_field_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            TaskResponse(task_id="task-1", task_name="Test", status="pending")
        assert "message" in str(exc_info.value)

    def test_incorrect_data_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            TaskResponse(
                task_id=123,
                task_name="Test",
                status="pending",
                message="OK",
            )

    def test_model_dump_serialization(self):
        response = TaskResponse(
            task_id="task-456",
            task_name="Sync",
            status="running",
            message="In progress",
        )
        dump = response.model_dump()
        assert dump == {
            "task_id": "task-456",
            "task_name": "Sync",
            "status": "running",
            "message": "In progress",
        }

    def test_empty_string_values_are_accepted(self):
        response = TaskResponse(
            task_id="",
            task_name="",
            status="",
            message="",
        )
        assert response.task_id == ""
        assert response.task_name == ""
        assert response.status == ""
        assert response.message == ""

    def test_extra_fields_ignored(self):
        response = TaskResponse(
            task_id="task-1",
            task_name="Test",
            status="done",
            message="OK",
            extra_field="should be ignored",
        )
        assert (
            not hasattr(response, "extra_field")
            or "extra_field" not in response.model_dump()
        )


# ============================================================
# TaskStatusResponse
# ============================================================


class TestTaskStatusResponse:
    """Tests for TaskStatusResponse schema."""

    def test_create_with_required_fields_only(self):
        response = TaskStatusResponse(task_id="task-1", status="pending")
        assert response.task_id == "task-1"
        assert response.status == "pending"
        assert response.result is None
        assert response.traceback is None
        assert response.progress is None

    def test_create_with_all_fields(self):
        response = TaskStatusResponse(
            task_id="task-2",
            status="failed",
            result={"key": "value"},
            traceback="Traceback: ...",
            progress={"percent": 50},
        )
        assert response.task_id == "task-2"
        assert response.status == "failed"
        assert response.result == {"key": "value"}
        assert response.traceback == "Traceback: ..."
        assert response.progress == {"percent": 50}

    def test_result_accepts_any_type(self):
        for value in [42, "string", [1, 2, 3], True, None, {"a": 1}]:
            response = TaskStatusResponse(task_id="t", status="s", result=value)
            assert response.result == value

    def test_missing_task_id_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            TaskStatusResponse(status="pending")
        assert "task_id" in str(exc_info.value)

    def test_missing_status_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            TaskStatusResponse(task_id="task-1")
        assert "status" in str(exc_info.value)

    def test_incorrect_type_for_task_id_raises_validation_error(self):
        with pytest.raises(ValidationError):
            TaskStatusResponse(task_id=12345, status="pending")

    def test_model_dump_serialization(self):
        response = TaskStatusResponse(
            task_id="task-10",
            status="completed",
            result="done",
            traceback=None,
            progress={"step": 3},
        )
        dump = response.model_dump()
        assert dump == {
            "task_id": "task-10",
            "status": "completed",
            "result": "done",
            "traceback": None,
            "progress": {"step": 3},
        }

    def test_null_values_for_optional_fields(self):
        response = TaskStatusResponse(
            task_id="t",
            status="s",
            result=None,
            traceback=None,
            progress=None,
        )
        assert response.result is None
        assert response.traceback is None
        assert response.progress is None


# ============================================================
# TaskInfo
# ============================================================


class TestTaskInfo:
    """Tests for TaskInfo schema."""

    def test_create_with_required_fields_only(self):
        info = TaskInfo(task_id="task-1", task_name="MyTask")
        assert info.task_id == "task-1"
        assert info.task_name == "MyTask"
        assert info.worker is None
        assert info.args == []
        assert info.kwargs == {}
        assert info.time_start is None
        assert info.eta is None

    def test_create_with_all_fields(self):
        info = TaskInfo(
            task_id="task-2",
            task_name="HeavyJob",
            worker="worker-01",
            args=[1, "two", 3.0],
            kwargs={"key": "value", "num": 42},
            time_start="2026-04-07T10:00:00",
            eta="2026-04-07T10:05:00",
        )
        assert info.task_id == "task-2"
        assert info.task_name == "HeavyJob"
        assert info.worker == "worker-01"
        assert info.args == [1, "two", 3.0]
        assert info.kwargs == {"key": "value", "num": 42}
        assert info.time_start == "2026-04-07T10:00:00"
        assert info.eta == "2026-04-07T10:05:00"

    def test_default_args_is_empty_list(self):
        info = TaskInfo(task_id="t", task_name="n")
        assert info.args == []
        # Verify it's a new list instance, not shared
        info.args.append(1)
        info2 = TaskInfo(task_id="t2", task_name="n2")
        assert info2.args == []

    def test_default_kwargs_is_empty_dict(self):
        info = TaskInfo(task_id="t", task_name="n")
        assert info.kwargs == {}
        # Verify it's a new dict instance, not shared
        info.kwargs["a"] = 1
        info2 = TaskInfo(task_id="t2", task_name="n2")
        assert info2.kwargs == {}

    def test_missing_task_id_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            TaskInfo(task_name="Test")
        assert "task_id" in str(exc_info.value)

    def test_missing_task_name_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            TaskInfo(task_id="t")
        assert "task_name" in str(exc_info.value)

    def test_incorrect_type_for_args_raises_validation_error(self):
        with pytest.raises(ValidationError):
            TaskInfo(task_id="t", task_name="n", args="not_a_list")

    def test_incorrect_type_for_kwargs_raises_validation_error(self):
        with pytest.raises(ValidationError):
            TaskInfo(task_id="t", task_name="n", kwargs="not_a_dict")

    def test_worker_accepts_string(self):
        info = TaskInfo(task_id="t", task_name="n", worker="w1")
        assert info.worker == "w1"

    def test_worker_accepts_none(self):
        info = TaskInfo(task_id="t", task_name="n", worker=None)
        assert info.worker is None

    def test_model_dump_serialization(self):
        info = TaskInfo(
            task_id="task-100",
            task_name="Report",
            worker="worker-5",
            args=["arg1"],
            kwargs={"verbose": True},
            time_start="2026-01-01",
            eta="2026-01-02",
        )
        dump = info.model_dump()
        assert dump == {
            "task_id": "task-100",
            "task_name": "Report",
            "worker": "worker-5",
            "args": ["arg1"],
            "kwargs": {"verbose": True},
            "time_start": "2026-01-01",
            "eta": "2026-01-02",
        }

    def test_empty_args_and_kwargs_in_dump(self):
        info = TaskInfo(task_id="t", task_name="n")
        dump = info.model_dump()
        assert dump["args"] == []
        assert dump["kwargs"] == {}


# ============================================================
# TaskListResponse
# ============================================================


class TestTaskListResponse:
    """Tests for TaskListResponse schema."""

    def test_create_with_valid_data(self):
        tasks = [
            TaskInfo(task_id="t1", task_name="Task1"),
            TaskInfo(task_id="t2", task_name="Task2"),
        ]
        response = TaskListResponse(tasks=tasks, total_count=2)
        assert len(response.tasks) == 2
        assert response.total_count == 2
        assert response.tasks[0].task_id == "t1"

    def test_empty_tasks_list(self):
        response = TaskListResponse(tasks=[], total_count=0)
        assert response.tasks == []
        assert response.total_count == 0

    def test_missing_tasks_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            TaskListResponse(total_count=0)
        assert "tasks" in str(exc_info.value)

    def test_missing_total_count_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            TaskListResponse(tasks=[])
        assert "total_count" in str(exc_info.value)

    def test_invalid_total_count_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            TaskListResponse(tasks=[], total_count="not_an_int")

    def test_invalid_tasks_list_raises_validation_error(self):
        with pytest.raises(ValidationError):
            TaskListResponse(tasks=["not_a_task_info"], total_count=1)

    def test_model_dump_serialization(self):
        tasks = [TaskInfo(task_id="t1", task_name="T1")]
        response = TaskListResponse(tasks=tasks, total_count=1)
        dump = response.model_dump()
        assert dump == {
            "tasks": [
                {
                    "task_id": "t1",
                    "task_name": "T1",
                    "worker": None,
                    "args": [],
                    "kwargs": {},
                    "time_start": None,
                    "eta": None,
                }
            ],
            "total_count": 1,
        }


# ============================================================
# BatchProcessRequest
# ============================================================


class TestBatchProcessRequest:
    """Tests for BatchProcessRequest schema."""

    def test_create_with_valid_data(self):
        req = BatchProcessRequest(record_ids=[1, 2, 3, 100])
        assert req.record_ids == [1, 2, 3, 100]

    def test_empty_record_ids(self):
        req = BatchProcessRequest(record_ids=[])
        assert req.record_ids == []

    def test_single_record_id(self):
        req = BatchProcessRequest(record_ids=[42])
        assert req.record_ids == [42]

    def test_missing_record_ids_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            BatchProcessRequest()
        assert "record_ids" in str(exc_info.value)

    def test_non_list_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BatchProcessRequest(record_ids="not_a_list")

    def test_non_int_elements_raises_validation_error(self):
        with pytest.raises(ValidationError):
            BatchProcessRequest(record_ids=[1, "two", 3])

    def test_negative_integers_accepted(self):
        req = BatchProcessRequest(record_ids=[-1, -100])
        assert req.record_ids == [-1, -100]

    def test_zero_accepted(self):
        req = BatchProcessRequest(record_ids=[0])
        assert req.record_ids == [0]

    def test_model_dump_serialization(self):
        req = BatchProcessRequest(record_ids=[10, 20])
        dump = req.model_dump()
        assert dump == {"record_ids": [10, 20]}


# ============================================================
# NotificationRequest
# ============================================================


class TestNotificationRequest:
    """Tests for NotificationRequest schema."""

    def test_create_with_required_fields_only(self):
        req = NotificationRequest(
            recipients=["user @example.com"],
            subject="Hello",
            message="Test message",
        )
        assert req.recipients == ["user @example.com"]
        assert req.subject == "Hello"
        assert req.message == "Test message"
        assert req.html_body is None

    def test_create_with_all_fields(self):
        req = NotificationRequest(
            recipients=["a @x.com", "b @x.com"],
            subject="Subject",
            message="Body",
            html_body="<p>HTML body</p>",
        )
        assert req.recipients == ["a @x.com", "b @x.com"]
        assert req.subject == "Subject"
        assert req.message == "Body"
        assert req.html_body == "<p>HTML body</p>"

    def test_empty_recipients_list(self):
        req = NotificationRequest(
            recipients=[],
            subject="Test",
            message="Msg",
        )
        assert req.recipients == []

    def test_empty_subject_and_message(self):
        req = NotificationRequest(
            recipients=["x @y.com"],
            subject="",
            message="",
        )
        assert req.subject == ""
        assert req.message == ""

    def test_missing_recipients_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            NotificationRequest(subject="S", message="M")
        assert "recipients" in str(exc_info.value)

    def test_missing_subject_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            NotificationRequest(recipients=["a @b.com"], message="M")
        assert "subject" in str(exc_info.value)

    def test_missing_message_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            NotificationRequest(recipients=["a @b.com"], subject="S")
        assert "message" in str(exc_info.value)

    def test_non_list_recipients_raises_validation_error(self):
        with pytest.raises(ValidationError):
            NotificationRequest(
                recipients="not_a_list",
                subject="S",
                message="M",
            )

    def test_non_string_elements_in_recipients_raises_validation_error(self):
        with pytest.raises(ValidationError):
            NotificationRequest(
                recipients=[123],
                subject="S",
                message="M",
            )

    def test_model_dump_serialization(self):
        req = NotificationRequest(
            recipients=["notify @test.com"],
            subject="Alert",
            message="Something happened",
            html_body="<b>Bold</b>",
        )
        dump = req.model_dump()
        assert dump == {
            "recipients": ["notify @test.com"],
            "subject": "Alert",
            "message": "Something happened",
            "html_body": "<b>Bold</b>",
        }


# ============================================================
# SystemAlertRequest
# ============================================================


class TestSystemAlertRequest:
    """Tests for SystemAlertRequest schema."""

    def test_create_with_required_fields_only(self):
        req = SystemAlertRequest(alert_type="error", message="Disk full")
        assert req.alert_type == "error"
        assert req.message == "Disk full"
        assert req.severity == "info"

    def test_create_with_custom_severity(self):
        req = SystemAlertRequest(
            alert_type="warning",
            message="High memory",
            severity="critical",
        )
        assert req.severity == "critical"

    def test_empty_alert_type_and_message(self):
        req = SystemAlertRequest(alert_type="", message="")
        assert req.alert_type == ""
        assert req.message == ""

    def test_missing_alert_type_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            SystemAlertRequest(message="Test")
        assert "alert_type" in str(exc_info.value)

    def test_missing_message_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            SystemAlertRequest(alert_type="info")
        assert "message" in str(exc_info.value)

    def test_non_string_alert_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            SystemAlertRequest(alert_type=123, message="test")

    def test_non_string_message_raises_validation_error(self):
        with pytest.raises(ValidationError):
            SystemAlertRequest(alert_type="info", message=456)

    def test_non_string_severity_raises_validation_error(self):
        with pytest.raises(ValidationError):
            SystemAlertRequest(alert_type="info", message="test", severity=99)

    def test_model_dump_serialization(self):
        req = SystemAlertRequest(
            alert_type="critical",
            message="System down",
            severity="urgent",
        )
        dump = req.model_dump()
        assert dump == {
            "alert_type": "critical",
            "message": "System down",
            "severity": "urgent",
        }

    def test_model_dump_with_default_severity(self):
        req = SystemAlertRequest(alert_type="info", message="FYI")
        dump = req.model_dump()
        assert dump["severity"] == "info"


# ============================================================
# CleanupRequest
# ============================================================


class TestCleanupRequest:
    """Tests for CleanupRequest schema."""

    def test_create_with_default_days_old(self):
        req = CleanupRequest()
        assert req.days_old == 30

    def test_create_with_custom_days_old(self):
        req = CleanupRequest(days_old=90)
        assert req.days_old == 90

    def test_zero_days_old(self):
        req = CleanupRequest(days_old=0)
        assert req.days_old == 0

    def test_negative_days_old(self):
        req = CleanupRequest(days_old=-7)
        assert req.days_old == -7

    def test_large_days_old(self):
        req = CleanupRequest(days_old=999999)
        assert req.days_old == 999999

    def test_float_raises_validation_error(self):
        # Pydantic v2 rejects floats for int fields
        with pytest.raises(ValidationError):
            CleanupRequest(days_old=7.9)

    def test_non_numeric_raises_validation_error(self):
        with pytest.raises(ValidationError):
            CleanupRequest(days_old="not_an_int")

    def test_model_dump_serialization(self):
        req = CleanupRequest(days_old=60)
        dump = req.model_dump()
        assert dump == {"days_old": 60}

    def test_model_dump_with_default(self):
        req = CleanupRequest()
        dump = req.model_dump()
        assert dump == {"days_old": 30}


# ============================================================
# ReportRequest
# ============================================================


class TestReportRequest:
    """Tests for ReportRequest schema."""

    def test_create_with_defaults(self):
        req = ReportRequest()
        assert req.start_date is None
        assert req.end_date is None
        assert req.report_type == "user"

    def test_create_with_all_fields(self):
        req = ReportRequest(
            start_date="2026-01-01",
            end_date="2026-04-07",
            report_type="system",
        )
        assert req.start_date == "2026-01-01"
        assert req.end_date == "2026-04-07"
        assert req.report_type == "system"

    def test_only_start_date(self):
        req = ReportRequest(start_date="2026-01-01")
        assert req.start_date == "2026-01-01"
        assert req.end_date is None
        assert req.report_type == "user"

    def test_only_end_date(self):
        req = ReportRequest(end_date="2026-12-31")
        assert req.start_date is None
        assert req.end_date == "2026-12-31"
        assert req.report_type == "user"

    def test_custom_report_type(self):
        req = ReportRequest(report_type="custom")
        assert req.report_type == "custom"

    def test_empty_report_type(self):
        req = ReportRequest(report_type="")
        assert req.report_type == ""

    def test_none_report_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ReportRequest(report_type=None)

    def test_non_string_start_date_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ReportRequest(start_date=12345)

    def test_model_dump_serialization(self):
        req = ReportRequest(
            start_date="2026-01-01",
            end_date="2026-06-30",
            report_type="financial",
        )
        dump = req.model_dump()
        assert dump == {
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
            "report_type": "financial",
        }

    def test_model_dump_with_defaults(self):
        req = ReportRequest()
        dump = req.model_dump()
        assert dump == {
            "start_date": None,
            "end_date": None,
            "report_type": "user",
        }


# ============================================================
# ExportRequest
# ============================================================


class TestExportRequest:
    """Tests for ExportRequest schema."""

    def test_create_with_defaults(self):
        req = ExportRequest()
        assert req.format == "json"
        assert req.include_files is False

    def test_create_with_custom_values(self):
        req = ExportRequest(format="csv", include_files=True)
        assert req.format == "csv"
        assert req.include_files is True

    def test_empty_format(self):
        req = ExportRequest(format="")
        assert req.format == ""

    def test_various_format_strings(self):
        for fmt in ["json", "csv", "xml", "yaml", "parquet"]:
            req = ExportRequest(format=fmt)
            assert req.format == fmt

    def test_include_files_true(self):
        req = ExportRequest(include_files=True)
        assert req.include_files is True

    def test_include_files_false(self):
        req = ExportRequest(include_files=False)
        assert req.include_files is False

    def test_none_format_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ExportRequest(format=None)

    def test_integer_coerced_to_bool_for_include_files(self):
        # Pydantic v2 coerces int 1 to True
        req = ExportRequest(include_files=1)
        assert req.include_files is True

    def test_string_coerced_to_bool_for_include_files(self):
        # Pydantic v2 coerces non-empty strings to True
        req = ExportRequest(include_files="yes")
        assert req.include_files is True

    def test_model_dump_serialization(self):
        req = ExportRequest(format="xml", include_files=True)
        dump = req.model_dump()
        assert dump == {"format": "xml", "include_files": True}

    def test_model_dump_with_defaults(self):
        req = ExportRequest()
        dump = req.model_dump()
        assert dump == {"format": "json", "include_files": False}
