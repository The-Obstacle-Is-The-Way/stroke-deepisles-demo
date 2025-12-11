"""API route handlers."""

import contextlib
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from stroke_deepisles_demo.api.schemas import CasesResponse, SegmentRequest, SegmentResponse
from stroke_deepisles_demo.data import list_case_ids
from stroke_deepisles_demo.metrics import compute_volume_ml
from stroke_deepisles_demo.pipeline import run_pipeline_on_case

router = APIRouter()

# Base directory for results
RESULTS_BASE = Path("/tmp/stroke-results")


def get_backend_base_url(request: Request) -> str:
    """Get the backend's public URL for building absolute file URLs.

    Priority:
    1. BACKEND_PUBLIC_URL env var (for production HF Spaces)
    2. Request's base URL (for local development)
    """
    env_url = os.environ.get("BACKEND_PUBLIC_URL", "").rstrip("/")
    if env_url:
        return env_url
    return str(request.base_url).rstrip("/")


@router.get("/cases", response_model=CasesResponse)
async def get_cases() -> CasesResponse:
    """List available cases from dataset."""
    try:
        cases = list_case_ids()
        return CasesResponse(cases=cases)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/segment", response_model=SegmentResponse)
async def run_segmentation(request: Request, body: SegmentRequest) -> SegmentResponse:
    """Run DeepISLES segmentation on a case."""
    try:
        # Generate unique run ID to avoid conflicts
        run_id = str(uuid.uuid4())[:8]
        output_dir = RESULTS_BASE / run_id

        result = run_pipeline_on_case(
            body.case_id,
            output_dir=output_dir,
            fast=body.fast_mode,
            compute_dice=True,
            cleanup_staging=True,
        )

        # Compute volume (may fail for edge cases)
        volume_ml = None
        with contextlib.suppress(Exception):
            volume_ml = round(compute_volume_ml(result.prediction_mask, threshold=0.5), 2)

        # Build absolute file URLs
        backend_url = get_backend_base_url(request)
        dwi_filename = result.input_files["dwi"].name
        pred_filename = result.prediction_mask.name

        file_path_prefix = f"/files/{run_id}/{result.case_id}"

        return SegmentResponse(
            caseId=result.case_id,
            diceScore=result.dice_score,
            volumeMl=volume_ml,
            elapsedSeconds=round(result.elapsed_seconds, 2),
            dwiUrl=f"{backend_url}{file_path_prefix}/{dwi_filename}",
            predictionUrl=f"{backend_url}{file_path_prefix}/{pred_filename}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
