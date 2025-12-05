"""DeepISLES stroke segmentation wrapper."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from stroke_deepisles_demo.core.exceptions import DeepISLESError, MissingInputError
from stroke_deepisles_demo.inference.docker import (
    DockerRunResult,
    ensure_gpu_available_if_requested,
    run_container,
)

if TYPE_CHECKING:
    from pathlib import Path

# Constants
DEEPISLES_IMAGE = "isleschallenge/deepisles"
EXPECTED_INPUT_FILES = ["dwi.nii.gz", "adc.nii.gz"]
OPTIONAL_INPUT_FILES = ["flair.nii.gz"]


@dataclass(frozen=True)
class DeepISLESResult:
    """Result of DeepISLES inference."""

    prediction_path: Path
    docker_result: DockerRunResult
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
    This function finds the most likely prediction file.

    Args:
        output_dir: DeepISLES output directory

    Returns:
        Path to the prediction mask NIfTI file

    Raises:
        DeepISLESError: If no prediction mask found
    """
    results_dir = output_dir / "results"

    # Check common output patterns
    possible_names = [
        "prediction.nii.gz",
        "pred.nii.gz",
        "lesion_mask.nii.gz",
        "output.nii.gz",
    ]

    for name in possible_names:
        pred_path = results_dir / name
        if pred_path.exists():
            return pred_path

    # Fall back to finding any .nii.gz in results dir
    if results_dir.exists():
        nifti_files = list(results_dir.glob("*.nii.gz"))
        if nifti_files:
            return nifti_files[0]

    raise DeepISLESError(
        f"No prediction mask found in {results_dir}. "
        "Expected files like 'prediction.nii.gz' or similar."
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

    Args:
        input_dir: Directory containing dwi.nii.gz, adc.nii.gz, [flair.nii.gz]
        output_dir: Where to write results (default: input_dir/results)
        fast: If True, use single-model mode (faster, slightly less accurate)
        gpu: If True, use GPU acceleration
        timeout: Maximum seconds to wait for inference

    Returns:
        DeepISLESResult with path to prediction mask

    Raises:
        DockerNotAvailableError: If Docker is not available
        DockerGPUNotAvailableError: If GPU requested but not available
        MissingInputError: If required input files are missing
        DeepISLESError: If inference fails (non-zero exit, missing output)

    Example:
        >>> result = run_deepisles_on_folder(Path("/data/case001"), fast=True)
        >>> print(result.prediction_path)
        /data/case001/results/prediction.nii.gz
    """
    start_time = time.time()

    # Validate inputs
    _dwi_path, _adc_path, flair_path = validate_input_folder(input_dir)

    # Check GPU if requested
    if gpu:
        ensure_gpu_available_if_requested(gpu)

    # Set up output directory
    if output_dir is None:
        output_dir = input_dir

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
