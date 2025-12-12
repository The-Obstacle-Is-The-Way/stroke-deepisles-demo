"""API configuration constants.

Single source of truth for API configuration values.
"""

from pathlib import Path

# Results directory for job outputs (must be in /tmp for HF Spaces)
# CRITICAL: This is the single source of truth. Import this instead of hardcoding.
RESULTS_DIR = Path("/tmp/stroke-results")

# Maximum concurrent jobs (pending + running)
# GPU inference is memory-intensive; too many concurrent jobs = OOM
# T4 GPU (16GB) can handle ~1-2 concurrent DeepISLES inferences safely
# Setting to 10 provides queue capacity while preventing runaway resource consumption
MAX_CONCURRENT_JOBS = 10
