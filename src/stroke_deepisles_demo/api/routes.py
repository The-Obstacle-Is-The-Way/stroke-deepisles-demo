"""API route handlers for stroke segmentation.

This module implements an async job queue pattern to handle long-running ML inference:
1. POST /api/segment creates a job and returns immediately (202 Accepted)
2. Background task runs the inference
3. Frontend polls GET /api/jobs/{job_id} for status/results

This pattern avoids HuggingFace Spaces' ~60s gateway timeout.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from stroke_deepisles_demo.api.job_store import JobStatus, get_job_store
from stroke_deepisles_demo.api.schemas import (
    CasesResponse,
    CreateJobResponse,
    JobStatusResponse,
    SegmentRequest,
    SegmentResponse,
)
from stroke_deepisles_demo.core.config import get_settings
from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.data import list_case_ids
from stroke_deepisles_demo.metrics import compute_volume_ml
from stroke_deepisles_demo.pipeline import run_pipeline_on_case

logger = get_logger(__name__)

router = APIRouter()


def get_backend_base_url(request: Request) -> str:
    """Get the backend's public URL for building absolute file URLs.

    Priority:
    1. BACKEND_PUBLIC_URL setting (from env var or config)
    2. Request's base URL (for local development)
    """
    settings_url = get_settings().backend_public_url
    if settings_url:
        return settings_url.rstrip("/")
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
    except Exception:
        logger.exception("Failed to list cases")
        raise HTTPException(status_code=500, detail="Failed to retrieve cases") from None


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
        # Concurrency limit to prevent GPU memory exhaustion (BUG-006 fix)
        store = get_job_store()
        if store.get_active_job_count() >= get_settings().max_concurrent_jobs:
            raise HTTPException(
                status_code=503,
                detail="Server busy: too many active jobs. Please try again later.",
            )

        # Validate case_id exists before creating job
        valid_cases = list_case_ids()
        if body.case_id not in valid_cases:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid case ID: '{body.case_id}'. Use GET /api/cases for available cases.",
            )

        # Use full UUID hex for uniqueness (no truncation)
        job_id = uuid.uuid4().hex
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

        # Note: Don't log case_id as it may be sensitive (medical domain)
        logger.info("Created segmentation job %s", job_id)

        return CreateJobResponse(
            jobId=job_id,
            status="pending",
            message=f"Segmentation job queued for {body.case_id}",
        )

    except HTTPException:
        # Re-raise HTTP exceptions (400, 404, 503, etc.) as-is
        # Without this, they'd be caught by `except Exception` and converted to 500
        raise
    except Exception:
        logger.exception("Failed to create segmentation job")
        raise HTTPException(status_code=500, detail="Failed to create segmentation job") from None


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
        output_dir = get_settings().results_dir / job_id

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

        # Compute volume - log failures but don't crash the job (BUG-011 fix)
        volume_ml = None
        try:
            volume_ml = round(compute_volume_ml(result.prediction_mask, threshold=0.5), 2)
        except (FileNotFoundError, ValueError) as e:
            # Expected failures: missing mask file or invalid threshold
            logger.warning("Could not compute volume for job %s: %s", job_id, e)
        except Exception:
            # Unexpected failures - log full traceback for debugging
            logger.exception("Unexpected error computing volume for job %s", job_id)

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
            "warning": "Results are temporary and will be lost if the Space restarts. Download promptly.",
        }

        # Mark as completed
        store.complete_job(job_id, result_data)

        # Note: Don't log case_id as it may be sensitive (medical domain)
        logger.info(
            "Job %s completed: dice=%.3f, time=%.1fs",
            job_id,
            result.dice_score or 0,
            result.elapsed_seconds,
        )

    except Exception:
        logger.exception("Job %s failed", job_id)
        # Sanitize error message - don't expose internal details to clients
        store.fail_job(job_id, "Segmentation failed")
