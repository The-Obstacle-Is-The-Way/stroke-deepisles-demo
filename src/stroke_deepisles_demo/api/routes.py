"""API route handlers for stroke segmentation.

This module implements an async job queue pattern to handle long-running ML inference:
1. POST /api/segment creates a job and returns immediately (202 Accepted)
2. Background task runs the inference
3. Frontend polls GET /api/jobs/{job_id} for status/results

This pattern avoids HuggingFace Spaces' ~60s gateway timeout.
"""

from __future__ import annotations

import contextlib
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from stroke_deepisles_demo.api.job_store import JobStatus, get_job_store
from stroke_deepisles_demo.api.schemas import (
    CasesResponse,
    CreateJobResponse,
    JobStatusResponse,
    SegmentRequest,
    SegmentResponse,
)
from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.data import list_case_ids
from stroke_deepisles_demo.metrics import compute_volume_ml
from stroke_deepisles_demo.pipeline import run_pipeline_on_case

logger = get_logger(__name__)

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
def get_cases() -> CasesResponse:
    """List available cases from dataset.

    Note: This is a sync def (not async) because list_case_ids() is synchronous.
    FastAPI automatically runs sync endpoints in a threadpool to avoid blocking.
    """
    try:
        cases = list_case_ids()
        return CasesResponse(cases=cases)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post(
    "/segment",
    response_model=CreateJobResponse,
    status_code=202,
    responses={
        202: {"description": "Job created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
def create_segment_job(
    request: Request,
    body: SegmentRequest,
    background_tasks: BackgroundTasks,
) -> CreateJobResponse:
    """Create an async segmentation job.

    Returns immediately with a job ID. The actual ML inference runs in the background.
    Poll GET /api/jobs/{jobId} for status updates and results.

    This async pattern is required because:
    - DeepISLES inference takes 30-60 seconds
    - HuggingFace Spaces has a ~60s gateway timeout
    - Returning immediately avoids timeout errors
    """
    try:
        job_id = str(uuid.uuid4())[:8]
        store = get_job_store()
        backend_url = get_backend_base_url(request)

        # Create job record
        store.create_job(job_id, body.case_id, body.fast_mode)

        # Queue background task
        background_tasks.add_task(
            run_segmentation_job,
            job_id=job_id,
            case_id=body.case_id,
            fast_mode=body.fast_mode,
            backend_url=backend_url,
        )

        logger.info("Created segmentation job %s for case %s", job_id, body.case_id)

        return CreateJobResponse(
            jobId=job_id,
            status="pending",
            message=f"Segmentation job queued for {body.case_id}",
        )

    except Exception as e:
        logger.exception("Failed to create segmentation job")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    responses={
        200: {"description": "Job status retrieved"},
        404: {"description": "Job not found"},
    },
)
def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the status of a segmentation job.

    Poll this endpoint to track job progress and retrieve results.

    Returns:
        Job status including progress percentage and results when completed.

    Raises:
        404: Job not found (may have expired or never existed)
    """
    store = get_job_store()
    job = store.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}. Jobs expire after 1 hour.",
        )

    # Build response from job data
    response = JobStatusResponse(
        jobId=job.id,
        status=job.status.value,
        progress=job.progress,
        progressMessage=job.progress_message,
        elapsedSeconds=round(job.elapsed_seconds, 2) if job.started_at else None,
        result=None,
        error=None,
    )

    # Include result if completed
    if job.status == JobStatus.COMPLETED and job.result:
        response.result = SegmentResponse(**job.result)

    # Include error if failed
    if job.status == JobStatus.FAILED and job.error:
        response.error = job.error

    return response


def run_segmentation_job(
    job_id: str,
    case_id: str,
    fast_mode: bool,
    backend_url: str,
) -> None:
    """Execute segmentation in background thread.

    This function runs in a threadpool (not the main event loop) because
    the ML inference is CPU/GPU-bound and blocking.

    Updates job status and progress throughout execution, allowing the
    frontend to show meaningful progress updates.

    Args:
        job_id: Unique job identifier
        case_id: Case to process
        fast_mode: Whether to use fast inference mode
        backend_url: Base URL for constructing result file URLs
    """
    store = get_job_store()
    job = store.get_job(job_id)

    if job is None:
        logger.error("Job %s not found when starting execution", job_id)
        return

    try:
        # Mark as running
        store.start_job(job_id)
        store.update_progress(job_id, 10, "Loading case data...")

        # Set up output directory
        output_dir = RESULTS_BASE / job_id

        store.update_progress(job_id, 20, "Staging files for DeepISLES...")

        # Run the pipeline
        store.update_progress(job_id, 30, "Running DeepISLES inference...")

        result = run_pipeline_on_case(
            case_id,
            output_dir=output_dir,
            fast=fast_mode,
            compute_dice=True,
            cleanup_staging=True,
        )

        store.update_progress(job_id, 85, "Computing metrics...")

        # Compute volume (may fail for edge cases)
        volume_ml = None
        with contextlib.suppress(Exception):
            volume_ml = round(compute_volume_ml(result.prediction_mask, threshold=0.5), 2)

        store.update_progress(job_id, 95, "Preparing results...")

        # Build result data
        dwi_filename = result.input_files["dwi"].name
        pred_filename = result.prediction_mask.name
        file_path_prefix = f"/files/{job_id}/{result.case_id}"

        result_data = {
            "caseId": result.case_id,
            "diceScore": result.dice_score,
            "volumeMl": volume_ml,
            "elapsedSeconds": round(result.elapsed_seconds, 2),
            "dwiUrl": f"{backend_url}{file_path_prefix}/{dwi_filename}",
            "predictionUrl": f"{backend_url}{file_path_prefix}/{pred_filename}",
        }

        # Mark as completed
        store.complete_job(job_id, result_data)

        logger.info(
            "Job %s completed: case=%s, dice=%.3f, time=%.1fs",
            job_id,
            case_id,
            result.dice_score or 0,
            result.elapsed_seconds,
        )

    except Exception as e:
        logger.exception("Job %s failed", job_id)
        store.fail_job(job_id, str(e))
