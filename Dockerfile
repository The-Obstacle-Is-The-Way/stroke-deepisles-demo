# Dockerfile for Hugging Face Spaces deployment
# Base: DeepISLES image with nnU-Net, SEALS, and all ML dependencies
# See: docs/specs/07-hf-spaces-deployment.md
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
FROM isleschallenge/deepisles:latest

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

# Copy requirements first for better layer caching
COPY --chown=1000:1000 requirements.txt /home/user/demo/requirements.txt

# Install Python dependencies into SYSTEM Python (NOT conda env)
# DeepISLES conda env is Python 3.8, but Gradio 6 needs Python 3.10+
# We'll shell out to conda env for inference only
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and package files
COPY --chown=1000:1000 pyproject.toml /home/user/demo/pyproject.toml
COPY --chown=1000:1000 README.md /home/user/demo/README.md
COPY --chown=1000:1000 src/ /home/user/demo/src/
COPY --chown=1000:1000 app.py /home/user/demo/app.py

# Copy adapter script for subprocess invocation of DeepISLES
# This script runs in the conda env (Py3.8) and is called via subprocess
COPY --chown=1000:1000 scripts/deepisles_adapter.py /app/deepisles_adapter.py

# Install the package itself into SYSTEM Python
# Using --no-deps since requirements.txt already installed dependencies
RUN pip install --no-cache-dir --no-deps -e .

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
RUN mkdir -p /home/user/demo/data /home/user/demo/results /home/user/demo/cache && \
    chown -R 1000:1000 /home/user/demo

# Switch to non-root user (required by HF Spaces)
USER user

# Expose the Gradio port
EXPOSE 7860

# Reset ENTRYPOINT from base image
ENTRYPOINT []

# Run Gradio app with SYSTEM Python (Py3.10+)
# DeepISLES inference is invoked via subprocess into conda env
CMD ["python", "-m", "stroke_deepisles_demo.ui.app"]
