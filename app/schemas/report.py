from datetime import date

from pydantic import BaseModel, Field, model_validator


class CsvExportRequest(BaseModel):
    """Request body for async CSV transaction export."""

    start_date: date
    end_date: date = Field(..., description="Inclusive end date for export range")

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class MonthlyReportRequest(BaseModel):
    """Request body for async monthly summary report generation."""

    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020)


class ReportJobResponse(BaseModel):
    """Response when a report generation job is queued."""

    task_id: str
    status: str = "pending"


class ReportTaskStatusResponse(BaseModel):
    """Poll status for a queued report generation task."""

    task_id: str
    status: str
    result: dict | None = None
