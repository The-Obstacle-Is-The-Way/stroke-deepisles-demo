# Quickstart

Get started with stroke-deepisles-demo in 5 minutes.

## Prerequisites

- Python 3.11+
- Docker (for DeepISLES inference)
- Node.js 18+ (for frontend development)
- ~10GB disk space (for Docker image and datasets)

## Installation

```bash
# Clone
git clone https://github.com/The-Obstacle-Is-The-Way/stroke-deepisles-demo.git
cd stroke-deepisles-demo

# Install Python dependencies
uv sync
```

## Pull DeepISLES Docker Image

```bash
docker pull isleschallenge/deepisles
```

## Run Locally

### Option 1: React SPA + FastAPI (Recommended)

Full-featured web interface with 3D NIfTI visualization via NiiVue.

```bash
# Terminal 1: Start FastAPI backend
uv run uvicorn stroke_deepisles_demo.api.main:app --reload --port 7860

# Terminal 2: Start React frontend
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### Option 2: CLI

```bash
# List available cases
uv run stroke-demo list

# Run on a specific case
uv run stroke-demo run --case sub-stroke0001 --fast
```

### Option 3: Python API

```python
from stroke_deepisles_demo.pipeline import run_pipeline_on_case

result = run_pipeline_on_case("sub-stroke0001", fast=True)
print(f"Dice score: {result.dice_score:.3f}")
print(f"Prediction: {result.prediction_mask}")
```

### Option 4: Legacy Gradio UI

The original Gradio interface is still available for backwards compatibility:

```bash
uv run python -m stroke_deepisles_demo.ui.app
# Open http://localhost:7860
```

Note: The Gradio UI does not support the async job queue or progress tracking.

## Configuration

Set environment variables or create a `.env` file:

```bash
# .env
STROKE_DEMO_LOG_LEVEL=DEBUG
STROKE_DEMO_DEEPISLES_USE_GPU=false  # If no GPU available
```

See [Configuration Guide](configuration.md) for all options.
