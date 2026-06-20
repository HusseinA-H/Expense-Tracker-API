import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_active_user
from app.celery_app import celery_app
from app.core.exceptions import AuthorizationError
from app.models.user import User
from app.schemas.report import (
    CsvExportRequest,
    MonthlyReportRequest,
    ReportJobResponse,
    ReportTaskStatusResponse,
)
from app.tasks.report_tasks import generate_csv_export, generate_monthly_report

router = APIRouter()
logger = structlog.get_logger("app.api.reports")


@router.post(
    "/export/csv",
    response_model=ReportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_csv_export(
    data: CsvExportRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Queue an async CSV export of the user's transactions."""
    task = generate_csv_export.delay(
        str(current_user.id),
        data.start_date.isoformat(),
        data.end_date.isoformat(),
    )
    logger.info(
        "CSV export queued",
        user_id=str(current_user.id),
        task_id=task.id,
    )
    return ReportJobResponse(task_id=task.id)


@router.post(
    "/export/monthly",
    response_model=ReportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_monthly_report(
    data: MonthlyReportRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Queue an async monthly summary report for the user."""
    task = generate_monthly_report.delay(
        str(current_user.id),
        data.month,
        data.year,
    )
    logger.info(
        "Monthly report queued",
        user_id=str(current_user.id),
        task_id=task.id,
        month=data.month,
        year=data.year,
    )
    return ReportJobResponse(task_id=task.id)


@router.get("/tasks/{task_id}", response_model=ReportTaskStatusResponse)
async def get_report_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Poll the status of a queued report generation task."""
    result: AsyncResult = celery_app.AsyncResult(task_id)

    if result.state == "PENDING":
        return ReportTaskStatusResponse(task_id=task_id, status="pending")

    if result.failed():
        return ReportTaskStatusResponse(
            task_id=task_id,
            status="failed",
            result={"error": str(result.result)},
        )

    if not result.ready():
        return ReportTaskStatusResponse(task_id=task_id, status=result.state.lower())

    payload = result.result
    if not isinstance(payload, dict):
        return ReportTaskStatusResponse(
            task_id=task_id, status="completed", result={"data": payload}
        )

    task_user_id = payload.get("user_id")
    if task_user_id and task_user_id != str(current_user.id):
        raise AuthorizationError(
            message="You do not have permission to view this task.",
            error_code="FORBIDDEN",
        )

    return ReportTaskStatusResponse(
        task_id=task_id,
        status=payload.get("status", "completed"),
        result=payload,
    )
