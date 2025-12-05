# Configuration

All settings can be configured via environment variables.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STROKE_DEMO_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `STROKE_DEMO_LOG_FORMAT` | `simple` | Log format (simple, detailed, json) |
| `STROKE_DEMO_HF_DATASET_ID` | `YongchengYAO/ISLES24-MR-Lite` | HuggingFace dataset ID |
| `STROKE_DEMO_HF_CACHE_DIR` | `None` | Custom HF cache directory |
| `STROKE_DEMO_HF_TOKEN` | `None` | HuggingFace API token (for private datasets) |
| `STROKE_DEMO_DEEPISLES_DOCKER_IMAGE` | `isleschallenge/deepisles` | DeepISLES Docker image |
| `STROKE_DEMO_DEEPISLES_FAST_MODE` | `true` | Use single-model mode |
| `STROKE_DEMO_DEEPISLES_TIMEOUT_SECONDS` | `1800` | Inference timeout |
| `STROKE_DEMO_DEEPISLES_USE_GPU` | `true` | Use GPU acceleration |
| `STROKE_DEMO_RESULTS_DIR` | `./results` | Directory for output files |
| `STROKE_DEMO_GRADIO_SERVER_NAME` | `0.0.0.0` | Gradio server host |
| `STROKE_DEMO_GRADIO_SERVER_PORT` | `7860` | Gradio server port |
| `STROKE_DEMO_GRADIO_SHARE` | `false` | Create public Gradio link |

## Using .env File

Create a `.env` file in the project root:

```bash
STROKE_DEMO_LOG_LEVEL=DEBUG
STROKE_DEMO_DEEPISLES_USE_GPU=false
STROKE_DEMO_RESULTS_DIR=/data/results
```

## Programmatic Configuration

```python
from stroke_deepisles_demo.core.config import settings, reload_settings
import os

# Check current settings
print(settings.log_level)

# Override via environment
os.environ["STROKE_DEMO_LOG_LEVEL"] = "DEBUG"
reload_settings()
print(settings.log_level)  # DEBUG
```
