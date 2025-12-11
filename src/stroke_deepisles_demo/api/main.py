"""FastAPI application for stroke segmentation API."""

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from stroke_deepisles_demo.api.routes import router

app = FastAPI(
    title="Stroke Segmentation API",
    description="DeepISLES stroke lesion segmentation",
    version="1.0.0",
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
    allow_origin_regex=r"https://.*--stroke-viewer-frontend(--.*)?\.hf\.space",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# Static files for NIfTI results (only mount if directory exists)
RESULTS_DIR = Path("/tmp/stroke-results")
if RESULTS_DIR.exists():
    app.mount("/files", StaticFiles(directory=str(RESULTS_DIR)), name="files")


@app.get("/")
async def root() -> dict[str, Any]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "stroke-segmentation-api"}
