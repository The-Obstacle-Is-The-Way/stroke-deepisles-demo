"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel


class CasesResponse(BaseModel):
    """Response for GET /api/cases."""

    cases: list[str]


class SegmentRequest(BaseModel):
    """Request body for POST /api/segment."""

    case_id: str
    fast_mode: bool = True


class SegmentResponse(BaseModel):
    """Response for POST /api/segment."""

    caseId: str
    diceScore: float | None
    volumeMl: float | None
    elapsedSeconds: float
    dwiUrl: str
    predictionUrl: str
