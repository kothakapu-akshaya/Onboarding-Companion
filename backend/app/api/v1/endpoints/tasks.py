"""API endpoints for managing Celery tasks and onboarding tasks."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.core.auth import get_current_active_user
from app.core.rbac_fastapi import require_any_role
from app.db.session import SessionDep
from app.models.task import Task
from app.models.user import User
from app.schemas.onboarding_task import (
    OnboardingTaskCreate,
    OnboardingTaskRead,
    OnboardingTaskUpdate,
)
from app.schemas.task import TaskResponse
from app.tasks.reports import export_user_data

router = APIRouter()


# -------------------------------------------------------------------------
# Existing Export API
# -------------------------------------------------------------------------


@router.post("/export-data", response_model=TaskResponse)
async def export_user_data_endpoint(
    export_format: str = "json",
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Export user's data."""
    try:
        task = export_user_data.delay(current_user.id, export_format)

        return TaskResponse(
            task_id=task.id,
            task_name="export_user_data",
            status="PENDING",
            message="Data export started",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------------
# Onboarding Task APIs
# -------------------------------------------------------------------------


@router.get("/", response_model=list[OnboardingTaskRead])
def list_tasks(
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
):
    """List all onboarding tasks."""
    tasks = session.exec(select(Task)).all()
    return [OnboardingTaskRead.model_validate(task) for task in tasks]


@router.post("/", response_model=OnboardingTaskRead, status_code=201)
def create_task(
    task_data: OnboardingTaskCreate,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
):
    """Create a new onboarding task."""
    task = Task(
        title=task_data.title,
        description=task_data.description,
        assigned_to=task_data.assigned_to,
        status="Pending",
    )

    session.add(task)
    session.commit()
    session.refresh(task)

    return OnboardingTaskRead.model_validate(task)


@router.patch("/{task_id}", response_model=OnboardingTaskRead)
def update_task(
    task_id: UUID,
    task_data: OnboardingTaskUpdate,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
):
    """Update onboarding task status."""
    task = session.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_data.status is not None:
        task.status = task_data.status

    task.updated_at = datetime.now(timezone.utc)

    session.add(task)
    session.commit()
    session.refresh(task)

    return OnboardingTaskRead.model_validate(task)
