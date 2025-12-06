"""DeepISLES stroke segmentation wrapper.

This module provides a unified interface for running DeepISLES segmentation.
It automatically detects the runtime environment and uses either:
- Docker invocation (local development with Docker)
- Direct Python invocation (HF Spaces, inside DeepISLES container)

See:
    - docs/specs/07-hf-spaces-deployment.md
    - https://github.com/ezequieldlrosa/DeepIsles
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from stroke_deepisles_demo.core.config import get_settings
from stroke_deepisles_demo.core.exceptions import DeepISLESError, MissingInputError
from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.inference.docker import (
    DockerRunResult,
    ensure_gpu_available_if_requested,
    run_container,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

# Constants
DEEPISLES_IMAGE = "isleschallenge/deepisles"
EXPECTED_INPUT_FILES = ["dwi.nii.gz", "adc.nii.gz"]
OPTIONAL_INPUT_FILES = ["flair.nii.gz"]


@dataclass(frozen=True)
class DeepISLESResult:
    """Result of DeepISLES inference."""

    prediction_path: Path
    docker_result: DockerRunResult | None  # None when using direct invocation
    elapsed_seconds: float


def validate_input_folder(input_dir: Path) -> tuple[Path, Path, Path | None]:
    """
    Validate that input folder contains required files.

    Args:
        input_dir: Directory to validate

    Returns:
        Tuple of (dwi_path, adc_path, flair_path_or_none)

    Raises:
        MissingInputError: If required files are missing
    """
    dwi_path = input_dir / "dwi.nii.gz"
    adc_path = input_dir / "adc.nii.gz"
    flair_path = input_dir / "flair.nii.gz"

    if not dwi_path.exists():
        raise MissingInputError(f"Required file 'dwi.nii.gz' not found in {input_dir}")

    if not adc_path.exists():
        raise MissingInputError(f"Required file 'adc.nii.gz' not found in {input_dir}")

    return dwi_path, adc_path, flair_path if flair_path.exists() else None


def find_prediction_mask(output_dir: Path) -> Path:
    """
    Find the prediction mask in DeepISLES output directory.

    DeepISLES outputs may have varying names depending on version.
    This function searches both the results subdirectory and the
    output directory itself.

    Args:
        output_dir: DeepISLES output directory

    Returns:
        Path to the prediction mask NIfTI file

    Raises:
        DeepISLESError: If no prediction mask found
    """
    # Check for results subdirectory (standard DeepISLES output structure)
    results_dir = output_dir / "results"
    search_dirs = [results_dir, output_dir] if results_dir.exists() else [output_dir]

    # Check common output patterns
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
        # Exclude input files that might have been copied
        nifti_files = list(search_dir.glob("*.nii.gz"))
        nifti_files = [
            f for f in nifti_files if not any(x in f.name.lower() for x in ["dwi", "adc", "flair"])
        ]
        if nifti_files:
            return nifti_files[0]

    raise DeepISLESError(
        f"No prediction mask found in {output_dir}. "
        "Expected files like 'prediction.nii.gz' or similar."
    )


def _run_via_docker(
    input_dir: Path,
    output_dir: Path,
    *,
    flair_path: Path | None,
    fast: bool,
    gpu: bool,
    timeout: float | None,
) -> DeepISLESResult:
    """
    Run DeepISLES via Docker container.

    This is the standard execution path for local development.
    """
    start_time = time.time()

    # Check GPU if requested
    if gpu:
        ensure_gpu_available_if_requested(gpu)

    # Build command arguments
    command: list[str] = [
        "--dwi_file_name",
        "dwi.nii.gz",
        "--adc_file_name",
        "adc.nii.gz",
    ]

    if flair_path is not None:
        command.extend(["--flair_file_name", "flair.nii.gz"])

    if fast:
        command.extend(["--fast", "True"])

    # Set up volume mounts
    volumes = {
        input_dir.resolve(): "/input",
        output_dir.resolve(): "/output",
    }

    logger.info("Running DeepISLES via Docker: input=%s, fast=%s, gpu=%s", input_dir, fast, gpu)

    # Run the container
    docker_result = run_container(
        DEEPISLES_IMAGE,
        command=command,
        volumes=volumes,
        gpu=gpu,
        timeout=timeout,
    )

    # Check for failure
    if docker_result.exit_code != 0:
        raise DeepISLESError(
            f"DeepISLES inference failed with exit code {docker_result.exit_code}. "
            f"stderr: {docker_result.stderr}"
        )

    # Find the prediction mask
    prediction_path = find_prediction_mask(output_dir)

    elapsed = time.time() - start_time

    return DeepISLESResult(
        prediction_path=prediction_path,
        docker_result=docker_result,
        elapsed_seconds=elapsed,
    )


def _run_via_direct_invocation(
    input_dir: Path,
    output_dir: Path,
    *,
    flair_path: Path | None,
    fast: bool,
) -> DeepISLESResult:
    """
    Run DeepISLES via direct Python invocation.

    This execution path is used on HF Spaces where Docker-in-Docker
    is not available. The container is based on isleschallenge/deepisles
    so all dependencies are pre-installed.
    """
    from stroke_deepisles_demo.inference.direct import run_deepisles_direct

    dwi_path = input_dir / "dwi.nii.gz"
    adc_path = input_dir / "adc.nii.gz"

    logger.info(
        "Running DeepISLES via direct invocation: input=%s, fast=%s",
        input_dir,
        fast,
    )

    result = run_deepisles_direct(
        dwi_path=dwi_path,
        adc_path=adc_path,
        output_dir=output_dir,
        flair_path=flair_path,
        fast=fast,
    )

    return DeepISLESResult(
        prediction_path=result.prediction_path,
        docker_result=None,  # No Docker result for direct invocation
        elapsed_seconds=result.elapsed_seconds,
    )


def run_deepisles_on_folder(
    input_dir: Path,
    *,
    output_dir: Path | None = None,
    fast: bool = True,
    gpu: bool = True,
    timeout: float | None = 1800,  # 30 minutes default
) -> DeepISLESResult:
    """
    Run DeepISLES stroke segmentation on a folder of NIfTI files.

    This function automatically selects the execution method based on
    the runtime environment:
    - Docker invocation: Used for local development
    - Direct invocation: Used on HF Spaces (Docker-in-Docker not available)

    Args:
        input_dir: Directory containing dwi.nii.gz, adc.nii.gz, [flair.nii.gz]
        output_dir: Where to write results (default: input_dir/results)
        fast: If True, use single-model mode (faster, slightly less accurate)
        gpu: If True, use GPU acceleration (only affects Docker mode)
        timeout: Maximum seconds to wait for inference (only affects Docker mode)

    Returns:
        DeepISLESResult with path to prediction mask

    Raises:
        DockerNotAvailableError: If Docker is not available (Docker mode only)
        DockerGPUNotAvailableError: If GPU requested but not available (Docker mode only)
        MissingInputError: If required input files are missing
        DeepISLESError: If inference fails (non-zero exit, missing output)

    Example:
        >>> result = run_deepisles_on_folder(Path("/data/case001"), fast=True)
        >>> print(result.prediction_path)
        /data/case001/results/prediction.nii.gz
    """
    # Validate inputs (validation ensures dwi/adc exist; we only need flair_path)
    _, _, flair_path = validate_input_folder(input_dir)

    # Set up output directory
    if output_dir is None:
        output_dir = input_dir

    # Check if we should use direct invocation
    settings = get_settings()
    use_direct = settings.use_direct_invocation

    if use_direct:
        logger.info(
            "Using direct DeepISLES invocation (HF Spaces mode: %s)",
            settings.is_hf_spaces,
        )
        return _run_via_direct_invocation(
            input_dir=input_dir,
            output_dir=output_dir,
            flair_path=flair_path,
            fast=fast,
        )
    else:
        logger.info("Using Docker-based DeepISLES invocation")
        return _run_via_docker(
            input_dir=input_dir,
            output_dir=output_dir,
            flair_path=flair_path,
            fast=fast,
            gpu=gpu,
            timeout=timeout,
        )
