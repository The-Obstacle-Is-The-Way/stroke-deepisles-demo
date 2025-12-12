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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

# CORS configuration
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "")
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative local port
]
if FRONTEND_ORIGIN:
    CORS_ORIGINS.append(FRONTEND_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # Match HF Spaces URLs in both formats:
    # - Direct: https://username-spacename.hf.space
    # - Proxy:  https://username--spacename--hash.hf.space
    allow_origin_regex=r"https://.*stroke-viewer-frontend.*\.hf\.space",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# Static files for NIfTI results
# Note: Directory created in lifespan startup before this runs
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
