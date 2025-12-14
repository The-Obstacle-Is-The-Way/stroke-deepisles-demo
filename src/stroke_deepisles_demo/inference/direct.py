"""Direct DeepISLES invocation via subprocess.

This module provides subprocess-based invocation of DeepISLES when running
on HF Spaces. We use subprocess because:
- DeepISLES runs in a conda env with Python 3.8
- Our FastAPI backend requires Python 3.11+ for modern dependencies
- The two environments are incompatible, so we bridge via subprocess

Usage:
    The subprocess calls /app/deepisles_adapter.py inside the isles_ensemble
    conda environment, which imports and runs IslesEnsemble.

See:
    - https://github.com/ezequieldlrosa/DeepIsles
    - docs/specs/07-hf-spaces-deployment.md
    - scripts/deepisles_adapter.py
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - used at runtime in dataclass and functions

from stroke_deepisles_demo.core.exceptions import DeepISLESError, MissingInputError
from stroke_deepisles_demo.core.logging import get_logger

logger = get_logger(__name__)

# Path to conda and adapter script in the Docker container
CONDA_PATH = "/opt/conda/bin/conda"
ADAPTER_SCRIPT = "/app/deepisles_adapter.py"
CONDA_ENV_NAME = "isles_ensemble"


@dataclass(frozen=True)
class DirectInvocationResult:
    """Result of direct DeepISLES invocation."""

    prediction_path: Path
    elapsed_seconds: float


def validate_input_files(
    dwi_path: Path,
    adc_path: Path,
    flair_path: Path | None = None,
) -> None:
    """
    Validate that input files exist.

    Args:
        dwi_path: Path to DWI NIfTI file
        adc_path: Path to ADC NIfTI file
        flair_path: Optional path to FLAIR NIfTI file

    Raises:
        MissingInputError: If required files are missing
    """
    if not dwi_path.exists():
        raise MissingInputError(f"DWI file not found: {dwi_path}")
    if not adc_path.exists():
        raise MissingInputError(f"ADC file not found: {adc_path}")
    if flair_path is not None and not flair_path.exists():
        raise MissingInputError(f"FLAIR file not found: {flair_path}")


def find_prediction_mask(output_dir: Path) -> Path:
    """
    Find the prediction mask in DeepISLES output directory.

    DeepISLES outputs the lesion mask as 'lesion_msk.nii.gz'.

    Args:
        output_dir: DeepISLES output directory

    Returns:
        Path to the prediction mask NIfTI file

    Raises:
        DeepISLESError: If no prediction mask found
    """
    # DeepISLES outputs lesion_msk.nii.gz
    expected_path = output_dir / "lesion_msk.nii.gz"
    if expected_path.exists():
        return expected_path

    # Fall back to searching for any NIfTI file
    nifti_files = list(output_dir.glob("*.nii.gz"))
    nifti_files = [
        f for f in nifti_files if not any(x in f.name.lower() for x in ["dwi", "adc", "flair"])
    ]
    if nifti_files:
        return nifti_files[0]

    raise DeepISLESError(
        f"No prediction mask found in {output_dir}. Expected 'lesion_msk.nii.gz' or similar."
    )


def run_deepisles_direct(
    dwi_path: Path,
    adc_path: Path,
    output_dir: Path,
    *,
    flair_path: Path | None = None,
    fast: bool = True,
    skull_strip: bool = False,  # noqa: ARG001 - kept for API compatibility
    parallelize: bool = True,  # noqa: ARG001 - kept for API compatibility
    save_team_outputs: bool = False,  # noqa: ARG001 - kept for API compatibility
    results_mni: bool = False,  # noqa: ARG001 - kept for API compatibility
    timeout: float = 1800,  # 30 minutes
) -> DirectInvocationResult:
    """
    Run DeepISLES segmentation via subprocess into conda environment.

    This function calls the deepisles_adapter.py script inside the
    isles_ensemble conda environment via subprocess. This bridges the
    Python version gap (Gradio needs 3.10+, DeepISLES needs 3.8).

    Args:
        dwi_path: Path to DWI NIfTI file (b=1000)
        adc_path: Path to ADC NIfTI file
        output_dir: Directory for output files
        flair_path: Optional path to FLAIR NIfTI file
        fast: If True, use SEALS model only (faster, no FLAIR needed)
        skull_strip: If True, perform skull stripping (not passed to subprocess)
        parallelize: If True, run models in parallel (not passed to subprocess)
        save_team_outputs: If True, save individual team outputs (not passed)
        results_mni: If True, output results in MNI space (not passed)
        timeout: Maximum seconds to wait for inference

    Returns:
        DirectInvocationResult with path to prediction mask

    Raises:
        DeepISLESError: If invocation fails
        MissingInputError: If required input files are missing

    Example:
        >>> result = run_deepisles_direct(
        ...     dwi_path=Path("/data/dwi.nii.gz"),
        ...     adc_path=Path("/data/adc.nii.gz"),
        ...     output_dir=Path("/data/output"),
        ...     fast=True
        ... )
        >>> print(result.prediction_path)
    """
    start_time = time.time()

    # Validate inputs
    validate_input_files(dwi_path, adc_path, flair_path)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Log paths at DEBUG to avoid exposing potentially sensitive path info at INFO
    logger.debug(
        "Running DeepISLES via subprocess: dwi=%s, adc=%s, flair=%s, fast=%s",
        dwi_path,
        adc_path,
        flair_path,
        fast,
    )

    # Build command to run adapter script in conda environment
    # Using: conda run -n isles_ensemble python /app/deepisles_adapter.py ...
    cmd = [
        CONDA_PATH,
        "run",
        "-n",
        CONDA_ENV_NAME,
        "python",
        ADAPTER_SCRIPT,
        "--dwi",
        str(dwi_path.resolve()),
        "--adc",
        str(adc_path.resolve()),
        "--output",
        str(output_dir.resolve()),
    ]

    if flair_path is not None:
        cmd.extend(["--flair", str(flair_path.resolve())])

    if fast:
        cmd.append("--fast")

    logger.debug("Subprocess command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/app",  # Run from DeepISLES directory
        )

        # Log verbose output at DEBUG to avoid log explosion
        # DeepISLES produces extensive stdout/stderr that would overwhelm INFO logs
        if result.stdout:
            logger.debug("DeepISLES stdout:\n%s", result.stdout)
        if result.stderr:
            # Log stderr at DEBUG unless it's a failure (handled below)
            logger.debug("DeepISLES stderr:\n%s", result.stderr)

        # Check for failure
        if result.returncode != 0:
            raise DeepISLESError(
                f"DeepISLES inference failed with exit code {result.returncode}. "
                f"stderr: {result.stderr}"
            )

    except subprocess.TimeoutExpired as e:
        raise DeepISLESError(f"DeepISLES inference timed out after {timeout} seconds") from e
    except FileNotFoundError as e:
        raise DeepISLESError(
            f"Failed to run DeepISLES subprocess: {e}. Is conda available at /opt/conda/bin/conda?"
        ) from e

    # Find the prediction mask
    prediction_path = find_prediction_mask(output_dir)

    elapsed = time.time() - start_time
    logger.info("DeepISLES subprocess completed in %.2fs", elapsed)

    return DirectInvocationResult(
        prediction_path=prediction_path,
        elapsed_seconds=elapsed,
    )
