# Configuration

All settings can be configured via environment variables with the `STROKE_DEMO_` prefix.

## Environment Variables

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `STROKE_DEMO_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `STROKE_DEMO_LOG_FORMAT` | `simple` | Log format (simple, detailed, json) |

### HuggingFace

| Variable | Default | Description |
|----------|---------|-------------|
| `STROKE_DEMO_HF_DATASET_ID` | `hugging-science/isles24-stroke` | HuggingFace dataset ID |
| `STROKE_DEMO_HF_TOKEN` | `None` | HuggingFace API token (for private/gated datasets) |

> **Note:** To control HF cache location, use the native `HF_HOME` env var (already set in Dockerfile).

### DeepISLES Inference

| Variable | Default | Description |
|----------|---------|-------------|
| `STROKE_DEMO_DEEPISLES_DOCKER_IMAGE` | `isleschallenge/deepisles` | DeepISLES Docker image |
| `STROKE_DEMO_DEEPISLES_FAST_MODE` | `true` | Use SEALS-only mode (faster, no FLAIR needed) |
| `STROKE_DEMO_DEEPISLES_TIMEOUT_SECONDS` | `1800` | Inference timeout (30 minutes) |
| `STROKE_DEMO_DEEPISLES_USE_GPU` | `true` | Use GPU acceleration (Docker mode only) |

### Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `STROKE_DEMO_RESULTS_DIR` | `/tmp/stroke-results` | Directory for job result files |

> **Note:** To control temp file location, use the native `TMPDIR` env var (Python's tempfile module respects it).

### API Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `STROKE_DEMO_MAX_CONCURRENT_JOBS` | `1` | Max concurrent inference jobs (increase for multi-GPU) |
| `STROKE_DEMO_FRONTEND_ORIGINS` | `["http://localhost:5173", "http://localhost:3000"]` | CORS allowed origins |
| `STROKE_DEMO_BACKEND_PUBLIC_URL` | `None` | Public URL for file links (auto-detected if not set) |

### Gradio UI (Legacy)

| Variable | Default | Description |
|----------|---------|-------------|
| `STROKE_DEMO_GRADIO_SERVER_NAME` | `0.0.0.0` | Gradio server host |
| `STROKE_DEMO_GRADIO_SERVER_PORT` | `7860` | Gradio server port |
| `STROKE_DEMO_GRADIO_SHARE` | `false` | Create public Gradio link |
| `STROKE_DEMO_GRADIO_SHOW_ERROR` | `false` | Show full tracebacks (security: keep false in prod) |

## Using .env File

Create a `.env` file in the project root:

```bash
STROKE_DEMO_LOG_LEVEL=DEBUG
STROKE_DEMO_DEEPISLES_USE_GPU=false
STROKE_DEMO_MAX_CONCURRENT_JOBS=2
```

## Programmatic Configuration

```python
from stroke_deepisles_demo.core.config import get_settings, reload_settings
import os

# Check current settings
print(get_settings().log_level)

# Override via environment
os.environ["STROKE_DEMO_LOG_LEVEL"] = "DEBUG"
reload_settings()
print(get_settings().log_level)  # DEBUG
```
