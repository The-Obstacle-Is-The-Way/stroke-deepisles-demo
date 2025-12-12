"""FastAPI application for stroke segmentation API.

This API provides async ML inference for stroke lesion segmentation using DeepISLES.
It implements a job queue pattern to handle long-running inference without timeouts:

1. POST /api/segment - Creates job, returns immediately (202)
2. GET /api/jobs/{id} - Poll for status/progress/results
3. GET /files/{job_id}/... - Download result NIfTI files

Architecture designed to work within HuggingFace Spaces constraints:
- ~60s gateway timeout (avoided via async job pattern)
- Single worker (in-memory job store is sufficient)
- /tmp writable only (results stored there)
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from stroke_deepisles_demo.api.files import files_router
from stroke_deepisles_demo.api.job_store import init_job_store
from stroke_deepisles_demo.api.routes import router
from stroke_deepisles_demo.core.config import get_settings
from stroke_deepisles_demo.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup/shutdown tasks.

    Startup:
    - Initialize job store with cleanup scheduler
    - Create results directory

    Shutdown:
    - Stop cleanup scheduler
    """
    # Startup
    logger.info("Starting stroke segmentation API...")
    settings = get_settings()

    # Check for GPU availability (DeepISLES requires GPU)
    try:
        import torch  # type: ignore[import-not-found]

        if not torch.cuda.is_available():
            logger.warning(
                "GPU not available! DeepISLES requires GPU for inference. "
                "This Space should be configured with t4-small or better hardware."
            )
    except ImportError:
        pass  # torch may not be available in all environments

    # Create results directory
    settings.results_dir.mkdir(parents=True, exist_ok=True)

    # Initialize job store with cleanup scheduler
    job_store = init_job_store(results_dir=settings.results_dir)
    logger.info("Job store initialized with %d jobs", len(job_store))

    yield

    # Shutdown
    logger.info("Shutting down stroke segmentation API...")
    job_store.stop_cleanup_scheduler()


app = FastAPI(
    title="Stroke Segmentation API",
    description="DeepISLES stroke lesion segmentation with async job queue",
    version="2.0.0",
    lifespan=lifespan,
)


# Cross-Origin Resource Policy middleware (required for COEP)
# This must be added BEFORE CORSMiddleware for proper header ordering
class CORPMiddleware(BaseHTTPMiddleware):
    """Add Cross-Origin-Resource-Policy header to all responses.

    Required when frontend uses COEP (Cross-Origin-Embedder-Policy: require-corp)
    to enable SharedArrayBuffer for WebGL performance optimizations.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        return response


# CORS configuration - Single source of truth from Settings
# Add CORP middleware first (for COEP compatibility)
app.add_middleware(CORPMiddleware)

# Add CORS middleware with settings for NiiVue binary file fetching
# Note: Using allow_origins list for exact matching (no regex needed)
# This eliminates regex security concerns while maintaining single source of truth
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().frontend_origins,
    allow_credentials=False,  # Not needed - no cookies/auth
    allow_methods=["GET", "POST", "HEAD"],  # HEAD for preflight checks
    allow_headers=["Content-Type", "Range"],  # Range needed for partial content requests
    expose_headers=["Content-Range", "Content-Length", "Accept-Ranges"],  # NiiVue needs these
)

# API routes (includes /api/* endpoints)
app.include_router(router, prefix="/api")

# File routes (serves NIfTI results through main app's middleware for CORS)
# BUG-004 FIX: Previously used StaticFiles mount which bypassed CORS middleware.
# Now using explicit routes so CORS headers are applied to file responses.
app.include_router(files_router)


@app.get("/")
async def root() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "stroke-segmentation-api",
        "version": "2.0.0",
        "features": ["async-jobs", "progress-tracking"],
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """Detailed health check endpoint."""
    from stroke_deepisles_demo.api.job_store import get_job_store

    store = get_job_store()
    settings = get_settings()
    return {
        "status": "healthy",
        "jobs_in_memory": len(store),
        "results_dir": str(settings.results_dir),
        "results_dir_exists": settings.results_dir.exists(),
    }
