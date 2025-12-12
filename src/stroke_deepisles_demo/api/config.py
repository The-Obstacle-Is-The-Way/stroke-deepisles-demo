"""API configuration constants.

Single source of truth for API configuration values.
"""

from pathlib import Path

# Results directory for job outputs (must be in /tmp for HF Spaces)
# CRITICAL: This is the single source of truth. Import this instead of hardcoding.
RESULTS_DIR = Path("/tmp/stroke-results")

# Maximum active jobs (pending + running) accepted by the API
# This limits how many jobs can be queued/running at once, NOT serialized GPU execution
# T4 GPU (16GB) can handle ~1-2 concurrent DeepISLES inferences safely
# Value of 10 allows reasonable queue depth while preventing unbounded accumulation
MAX_CONCURRENT_JOBS = 10
