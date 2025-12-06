# Dockerfile for Hugging Face Spaces deployment
# Base: DeepISLES image with nnU-Net, SEALS, and all ML dependencies
# See: docs/specs/07-hf-spaces-deployment.md
#
# IMPORTANT: During Docker build, GPU is NOT available.
# All GPU operations happen at runtime only.

FROM isleschallenge/deepisles:latest

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# HF Spaces runs containers with user ID 1000
# Create user if not exists (DeepISLES image may already have a user)
RUN useradd -m -u 1000 user 2>/dev/null || true

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY --chown=1000:1000 requirements.txt /app/requirements.txt

# Install Python dependencies (extras only - DeepISLES image has PyTorch, nnUNet, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and package files
COPY --chown=1000:1000 pyproject.toml /app/pyproject.toml
COPY --chown=1000:1000 README.md /app/README.md
COPY --chown=1000:1000 src/ /app/src/
COPY --chown=1000:1000 app.py /app/app.py

# Install the package itself (makes stroke_deepisles_demo importable)
# Using --no-deps since requirements.txt already installed dependencies
RUN pip install --no-cache-dir --no-deps -e .

# Set environment variable to indicate we're running in HF Spaces
# This allows the app to detect runtime environment and use direct invocation
ENV HF_SPACES=1
ENV DEEPISLES_DIRECT_INVOCATION=1

# Create directories for data with proper permissions
RUN mkdir -p /app/data /app/results /app/cache && \
    chown -R 1000:1000 /app

# Switch to non-root user (required by HF Spaces)
USER user

# Expose the Gradio port
EXPOSE 7860

# Set the default command
# Use Gradio's built-in server settings for HF Spaces
CMD ["python", "-m", "stroke_deepisles_demo.ui.app"]
