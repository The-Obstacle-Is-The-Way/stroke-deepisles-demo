"""Pydantic schemas for API requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field


class CasesResponse(BaseModel):
    """Response for GET /api/cases."""

    cases: list[str]


class SegmentRequest(BaseModel):
    """Request body for POST /api/segment."""

    case_id: str
    fast_mode: bool = True


class SegmentResponse(BaseModel):
    """Segmentation result data (embedded in job response when completed)."""

    caseId: str
    diceScore: float | None
    volumeMl: float | None
    elapsedSeconds: float
    dwiUrl: str
    predictionUrl: str
    warning: str | None = Field(
        None, description="Warning message about result storage (e.g., ephemeral disk)"
    )


# Job status type for strong typing
JobStatusType = Literal["pending", "running", "completed", "failed"]


class CreateJobResponse(BaseModel):
    """Response for POST /api/segment (async job creation).

    Returns immediately with job ID. Client should poll GET /api/jobs/{jobId}
    for status updates and results.
    """

    jobId: str = Field(..., description="Unique job identifier for polling")
    status: JobStatusType = Field(..., description="Initial job status (always 'pending')")
    message: str = Field(..., description="Human-readable status message")


class JobStatusResponse(BaseModel):
    """Response for GET /api/jobs/{job_id}.

    Provides current job status, progress, and results when completed.
    """

    jobId: str = Field(..., description="Unique job identifier")
    status: JobStatusType = Field(..., description="Current job status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    progressMessage: str = Field(..., description="Human-readable progress status")
    elapsedSeconds: float | None = Field(
        None, description="Time elapsed since job started (seconds)"
    )
    result: SegmentResponse | None = Field(
        None, description="Segmentation results (only present when status='completed')"
    )
    error: str | None = Field(None, description="Error message (only present when status='failed')")


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str = Field(..., description="Error description")
