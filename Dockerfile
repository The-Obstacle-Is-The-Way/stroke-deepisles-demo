# Dockerfile for Hugging Face Spaces deployment (FastAPI backend)
# Base: DeepISLES image with nnU-Net, SEALS, and all ML dependencies
# See: docs/specs/frontend/36-frontend-without-gradio-hf-spaces.md
#
# IMPORTANT: During Docker build, GPU is NOT available.
# All GPU operations happen at runtime only.
#
# CRITICAL: DeepISLES code lives at /app/src/ in the base image.
# We install our demo at /home/user/demo to avoid overwriting DeepISLES.

# NOTE: isleschallenge/deepisles only publishes 'latest' tag on Docker Hub.
# For reproducibility, consider using a SHA digest if available:
#   FROM isleschallenge/deepisles@sha256:<digest>
# Check https://hub.docker.com/r/isleschallenge/deepisles/tags for updates.
# Current base: DeepISLES v1.1 (as of Dec 2025)
FROM isleschallenge/deepisles@sha256:848c9eceb67dbc585bcb37f093389d142caeaa98878bd31039af04ef297a5af4

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# HF Spaces runs containers with user ID 1000
# Create user if not exists (DeepISLES image may already have a user)
RUN useradd -m -u 1000 user 2>/dev/null || true

# IMPORTANT: Use /home/user/demo for our app, NOT /app
# /app contains DeepISLES code (main.py, src/, weights/) that we must NOT overwrite
WORKDIR /home/user/demo

# Copy dependency files for reproducible installs
COPY --chown=1000:1000 pyproject.toml uv.lock /home/user/demo/

# Install uv for reproducible dependency management
RUN pip install --no-cache-dir uv

# Create virtual environment and add to PATH
ENV VIRTUAL_ENV=/home/user/demo/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies from lock file (frozen = fail if lock stale)
# This ensures CI, local dev, and production use IDENTICAL versions
# CRITICAL: --extra api installs FastAPI/uvicorn required by CMD
RUN uv sync --frozen --no-dev --no-install-project --extra api

# Copy application source code and package files
COPY --chown=1000:1000 README.md /home/user/demo/README.md
COPY --chown=1000:1000 src/ /home/user/demo/src/

# Copy adapter script for subprocess invocation of DeepISLES
# This script runs in the conda env (Py3.8) and is called via subprocess
COPY --chown=1000:1000 scripts/deepisles_adapter.py /app/deepisles_adapter.py

# Install the package itself (dependencies already installed from lock)
RUN uv pip install --no-deps -e .

# Set environment variable to indicate we're running in HF Spaces
# This allows the app to detect runtime environment and use direct invocation
ENV HF_SPACES=1
ENV DEEPISLES_DIRECT_INVOCATION=1

# Point to DeepISLES location for direct invocation
# DeepISLES code is at /app in the base image
ENV DEEPISLES_PATH=/app

# Ensure HuggingFace cache uses our writable directory
ENV HF_HOME=/home/user/demo/cache

# Create directories for data with proper permissions
# /tmp/stroke-results stores job result files, served via explicit /files/{job_id}/ routes
RUN mkdir -p /home/user/demo/data /home/user/demo/results /home/user/demo/cache /tmp/stroke-results && \
    chown -R 1000:1000 /home/user/demo /tmp/stroke-results

# Switch to non-root user (required by HF Spaces)
USER user

# Expose the API port (HF Spaces expects 7860)
EXPOSE 7860

# Reset ENTRYPOINT from base image
ENTRYPOINT []

# Explicit frontend origin for CORS
ENV STROKE_DEMO_FRONTEND_ORIGINS='["https://vibecodermcswaggins-stroke-viewer-frontend.hf.space"]'

# Explicit backend public URL for constructing file URLs
# This ensures correct https:// URLs even if proxy headers aren't forwarded correctly
ENV STROKE_DEMO_BACKEND_PUBLIC_URL=https://vibecodermcswaggins-stroke-deepisles-demo.hf.space

# Results directory (matches default in code, but explicit is better)
ENV STROKE_DEMO_RESULTS_DIR=/tmp/stroke-results

# Run FastAPI with uvicorn (module path: stroke_deepisles_demo.api.main:app)
# --proxy-headers: Trust X-Forwarded-Proto from HF Spaces proxy (ensures https:// in request.base_url)
CMD ["uvicorn", "stroke_deepisles_demo.api.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers"]
