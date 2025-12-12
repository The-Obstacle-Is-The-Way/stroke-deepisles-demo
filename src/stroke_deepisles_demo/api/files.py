"""File serving routes for NIfTI result files.

BUG-004 FIX: This module replaces the StaticFiles mount approach.

Previously, files were served via:
    app.mount("/files", StaticFiles(directory=RESULTS_DIR))

The problem: StaticFiles is a mounted sub-application, and FastAPI/Starlette
middleware (including CORSMiddleware) does NOT propagate to mounted apps.
This caused NiiVue's cross-origin fetch to fail with "Failed to fetch".

Solution: Use explicit route handlers that go through the main app's middleware.
Now CORS headers are correctly applied to file responses.

Reference: https://github.com/fastapi/fastapi/discussions/7319
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from stroke_deepisles_demo.api.config import RESULTS_DIR
from stroke_deepisles_demo.core.logging import get_logger

logger = get_logger(__name__)

files_router = APIRouter(prefix="/files", tags=["files"])


@files_router.get("/{job_id}/{case_id}/{filename}")
async def get_result_file(job_id: str, case_id: str, filename: str) -> FileResponse:
    """Serve NIfTI result files with proper CORS headers.

    This route goes through the main FastAPI app's middleware stack,
    ensuring CORS and CORP headers are applied to the response.

    Args:
        job_id: The job UUID from segmentation
        case_id: The case identifier (e.g., sub-stroke0001)
        filename: The NIfTI filename (e.g., dwi.nii.gz, prediction_fused.nii.gz)

    Returns:
        FileResponse with the NIfTI file

    Raises:
        404: File not found (job expired, invalid path, or doesn't exist)
    """
    # Construct file path
    file_path = RESULTS_DIR / job_id / case_id / filename

    # Security: Ensure path doesn't escape RESULTS_DIR (path traversal protection)
    # Using is_relative_to() instead of startswith() to prevent prefix-collision bypass
    # e.g., /tmp/stroke-results-evil/file.txt would pass startswith but fail is_relative_to
    try:
        base_dir = RESULTS_DIR.resolve()
        resolved = file_path.resolve()
        if not resolved.is_relative_to(base_dir):
            logger.warning("Path traversal attempt blocked: %s", filename)
            raise HTTPException(status_code=404, detail="File not found")
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="Invalid file path") from None

    # Check file exists
    if not resolved.exists() or not resolved.is_file():
        logger.debug("File not found: %s", resolved)
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}. Job may have expired (1 hour TTL).",
        )

    # Determine media type based on extension
    # NIfTI files are typically gzip-compressed
    if filename.endswith(".nii.gz"):
        media_type = "application/gzip"
    elif filename.endswith(".nii"):
        media_type = "application/octet-stream"
    else:
        media_type = "application/octet-stream"

    logger.debug("Serving file: %s (type: %s)", resolved, media_type)

    return FileResponse(
        path=resolved,
        media_type=media_type,
        filename=filename,
    )
