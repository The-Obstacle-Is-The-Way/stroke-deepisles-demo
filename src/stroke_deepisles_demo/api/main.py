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

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from stroke_deepisles_demo.api.job_store import init_job_store
from stroke_deepisles_demo.api.routes import router
from stroke_deepisles_demo.core.logging import get_logger

logger = get_logger(__name__)

# Results directory (must be in /tmp for HF Spaces)
RESULTS_DIR = Path("/tmp/stroke-results")


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
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize job store with cleanup scheduler
    job_store = init_job_store(results_dir=RESULTS_DIR)
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


# CORS configuration - Single source of truth (no regex needed for exact origins)
# Production HF Space frontend origin
HF_SPACE_FRONTEND = "https://vibecodermcswaggins-stroke-viewer-frontend.hf.space"

CORS_ORIGINS: list[str] = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative local port
    HF_SPACE_FRONTEND,  # Production HF Space frontend
]

# Allow override via environment variable (for custom deployments)
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "")
if FRONTEND_ORIGIN and FRONTEND_ORIGIN not in CORS_ORIGINS:
    CORS_ORIGINS.append(FRONTEND_ORIGIN)

# Add CORP middleware first (for COEP compatibility)
app.add_middleware(CORPMiddleware)

# Add CORS middleware with strict security settings
# Note: Using allow_origins list for exact matching (no regex needed)
# This eliminates regex security concerns while maintaining single source of truth
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,  # Not needed - no cookies/auth
    allow_methods=["GET", "POST"],  # Only methods we use
    allow_headers=["Content-Type"],  # Only headers we need
)

# API routes
app.include_router(router, prefix="/api")

# Static files for NIfTI results
# Note: Mount happens at import time; ensure directory exists here as well.
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(RESULTS_DIR)), name="files")


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
    return {
        "status": "healthy",
        "jobs_in_memory": len(store),
        "results_dir": str(RESULTS_DIR),
        "results_dir_exists": RESULTS_DIR.exists(),
    }
