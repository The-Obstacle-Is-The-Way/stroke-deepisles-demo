"""Direct DeepISLES invocation without Docker.

This module provides direct Python invocation of DeepISLES when running
inside the DeepISLES Docker image (e.g., on HF Spaces). This avoids
Docker-in-Docker which is not supported on HF Spaces.

Usage:
    When running in HF Spaces, our container is based on isleschallenge/deepisles,
    which has all DeepISLES dependencies pre-installed. This module imports
    and calls DeepISLES directly.

See:
    - https://github.com/ezequieldlrosa/DeepIsles
    - docs/specs/07-hf-spaces-deployment.md
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

from stroke_deepisles_demo.core.exceptions import DeepISLESError, MissingInputError
from stroke_deepisles_demo.core.logging import get_logger

logger = get_logger(__name__)

# Paths where DeepISLES source might be located in the Docker image
DEEPISLES_SEARCH_PATHS = [
    "/app",
    "/DeepIsles",
    "/opt/deepisles",
    "/home/user/DeepIsles",
]


@dataclass(frozen=True)
class DirectInvocationResult:
    """Result of direct DeepISLES invocation."""

    prediction_path: Path
    elapsed_seconds: float
    stdout: str = ""
    stderr: str = ""


def _ensure_deepisles_importable() -> str:
    """
    Ensure DeepISLES modules are importable by adding to sys.path.

    Returns:
        Path where DeepISLES was found

    Raises:
        DeepISLESError: If DeepISLES cannot be found
    """
    for path in DEEPISLES_SEARCH_PATHS:
        if Path(path).exists():
            if path not in sys.path:
                sys.path.insert(0, path)
            try:
                # Test import (only available in DeepISLES Docker image)
                from src.isles22_ensemble import IslesEnsemble  # noqa: F401

                logger.debug("Found DeepISLES at %s", path)
                return path
            except ImportError:
                continue

    raise DeepISLESError(
        "DeepISLES modules not found. Direct invocation requires running "
        "inside the DeepISLES Docker image. Searched paths: "
        f"{DEEPISLES_SEARCH_PATHS}"
    )


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


def run_deepisles_direct(
    dwi_path: Path,
    adc_path: Path,
    output_dir: Path,
    *,
    flair_path: Path | None = None,
    fast: bool = True,
    skull_strip: bool = False,
    parallelize: bool = True,
    save_team_outputs: bool = False,
    results_mni: bool = False,
) -> DirectInvocationResult:
    """
    Run DeepISLES segmentation via direct Python invocation.

    This function calls the DeepISLES IslesEnsemble.predict_ensemble() method
    directly, bypassing Docker. It's used when running inside the DeepISLES
    container on HF Spaces.

    Args:
        dwi_path: Path to DWI NIfTI file (b=1000)
        adc_path: Path to ADC NIfTI file
        output_dir: Directory for output files
        flair_path: Optional path to FLAIR NIfTI file
        fast: If True, use SEALS model only (faster, no FLAIR needed)
        skull_strip: If True, perform skull stripping
        parallelize: If True, run models in parallel
        save_team_outputs: If True, save individual team outputs
        results_mni: If True, output results in MNI space

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

    # Ensure DeepISLES is importable
    deepisles_path = _ensure_deepisles_importable()

    # Import DeepISLES (only available in DeepISLES Docker image)
    try:
        from src.isles22_ensemble import IslesEnsemble
    except ImportError as e:
        raise DeepISLESError(f"Failed to import DeepISLES: {e}") from e

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Running DeepISLES direct invocation: dwi=%s, adc=%s, flair=%s, fast=%s",
        dwi_path,
        adc_path,
        flair_path,
        fast,
    )

    try:
        # Initialize the ensemble
        stroke_segm = IslesEnsemble()

        # Run prediction
        stroke_segm.predict_ensemble(
            ensemble_path=deepisles_path,
            input_dwi_path=str(dwi_path),
            input_adc_path=str(adc_path),
            input_flair_path=str(flair_path) if flair_path else None,
            output_path=str(output_dir),
            skull_strip=skull_strip,
            fast=fast,
            save_team_outputs=save_team_outputs,
            results_mni=results_mni,
            parallelize=parallelize,
        )
    except Exception as e:
        raise DeepISLESError(f"DeepISLES inference failed: {e}") from e

    # Find the prediction mask
    prediction_path = _find_prediction_mask(output_dir)

    elapsed = time.time() - start_time
    logger.info("DeepISLES direct invocation completed in %.2fs", elapsed)

    return DirectInvocationResult(
        prediction_path=prediction_path,
        elapsed_seconds=elapsed,
    )


def _find_prediction_mask(output_dir: Path) -> Path:
    """
    Find the prediction mask in the output directory.

    Args:
        output_dir: DeepISLES output directory

    Returns:
        Path to the prediction mask NIfTI file

    Raises:
        DeepISLESError: If no prediction mask found
    """
    # Check for results subdirectory
    results_dir = output_dir / "results"
    search_dirs = [results_dir, output_dir] if results_dir.exists() else [output_dir]

    # Common output patterns from DeepISLES
    possible_names = [
        "prediction.nii.gz",
        "pred.nii.gz",
        "lesion_mask.nii.gz",
        "output.nii.gz",
        "ensemble_prediction.nii.gz",
    ]

    for search_dir in search_dirs:
        for name in possible_names:
            pred_path = search_dir / name
            if pred_path.exists():
                return pred_path

        # Fall back to finding any .nii.gz in the directory
        nifti_files = list(search_dir.glob("*.nii.gz"))
        # Filter out input files
        nifti_files = [
            f
            for f in nifti_files
            if not any(x in f.name.lower() for x in ["dwi", "adc", "flair"])
        ]
        if nifti_files:
            return nifti_files[0]

    raise DeepISLESError(
        f"No prediction mask found in {output_dir}. "
        "Expected files like 'prediction.nii.gz' or similar."
    )
