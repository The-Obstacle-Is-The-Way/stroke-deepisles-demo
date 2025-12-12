"""API configuration constants.

Single source of truth for API configuration values.
"""

from pathlib import Path

# Results directory for job outputs (must be in /tmp for HF Spaces)
# CRITICAL: This is the single source of truth. Import this instead of hardcoding.
RESULTS_DIR = Path("/tmp/stroke-results")
