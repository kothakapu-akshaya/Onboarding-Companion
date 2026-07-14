"""Pydantic schemas for task-related API responses."""

from typing import Any

from pydantic import BaseModel


class TaskResponse(BaseModel):
    """Response schema for task creation."""

    task_id: str
    task_name: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response schema for task status."""

    task_id: str
    status: str
    result: Any | None = None
    traceback: str | None = None
    progress: dict[str, Any] | None = None


class TaskInfo(BaseModel):
    """Schema for task information."""

    task_id: str
    task_name: str
    worker: str | None = None
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    time_start: str | None = None
    eta: str | None = None


class TaskListResponse(BaseModel):
    """Response schema for task lists."""

    tasks: list[TaskInfo]
    total_count: int


class BatchProcessRequest(BaseModel):
    """Request schema for batch processing."""

    record_ids: list[int]


class NotificationRequest(BaseModel):
    """Request schema for sending notifications."""

    recipients: list[str]
    subject: str
    message: str
    html_body: str | None = None


class SystemAlertRequest(BaseModel):
    """Request schema for system alerts."""

    alert_type: str
    message: str
    severity: str = "info"


class CleanupRequest(BaseModel):
    """Request schema for cleanup tasks."""

    days_old: int = 30


class ReportRequest(BaseModel):
    """Request schema for report generation."""

    start_date: str | None = None
    end_date: str | None = None
    report_type: str = "user"


class ExportRequest(BaseModel):
    """Request schema for data export."""

    format: str = "json"
    include_files: bool = False
