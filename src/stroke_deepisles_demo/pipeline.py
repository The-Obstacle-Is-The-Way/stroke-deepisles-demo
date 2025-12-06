"""End-to-end pipeline orchestration."""

from __future__ import annotations

import shutil
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from stroke_deepisles_demo import metrics
from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.data import load_isles_dataset, stage_case_for_deepisles
from stroke_deepisles_demo.inference import run_deepisles_on_folder

if TYPE_CHECKING:
    from collections.abc import Sequence

    from stroke_deepisles_demo.core.types import CaseFiles

logger = get_logger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    """Complete result of running the pipeline on a case."""

    case_id: str
    input_files: CaseFiles
    staged_dir: Path
    prediction_mask: Path
    ground_truth: Path | None
    dice_score: float | None  # None if ground truth unavailable or not computed
    elapsed_seconds: float


@dataclass(frozen=True)
class PipelineSummary:
    """Summary statistics from multiple pipeline runs."""

    num_cases: int
    num_successful: int
    num_failed: int
    mean_dice: float | None
    std_dice: float | None
    min_dice: float | None
    max_dice: float | None
    mean_elapsed_seconds: float


def run_pipeline_on_case(
    case_id: str | int,
    *,
    dataset_id: str | None = None,
    output_dir: Path | None = None,
    fast: bool = True,
    gpu: bool = True,
    compute_dice: bool = True,
    cleanup_staging: bool = False,
) -> PipelineResult:
    """
    Run the complete segmentation pipeline on a single case.

    Args:
        case_id: Case identifier (string) or index (int)
        dataset_id: HF dataset ID (default from settings - currently ignored/local)
        output_dir: Directory for results (default: temp dir)
        fast: Use SEALS-only mode (ISLES'22 winner, DWI+ADC only, no FLAIR needed)
        gpu: Use GPU acceleration
        compute_dice: Compute Dice score if ground truth available
        cleanup_staging: Remove staging directory after inference

    Returns:
        PipelineResult with all paths and optional metrics
    """
    # Note: dataset_id is currently unused as we default to local loading.
    # It's kept for interface compatibility with future cloud mode.
    _ = dataset_id

    start_time = time.time()

    # 1. Load Dataset
    dataset = load_isles_dataset()  # Uses default local path for now

    # Resolve ID if integer
    if isinstance(case_id, int):
        all_ids = dataset.list_case_ids()
        if case_id < 0 or case_id >= len(all_ids):
            raise IndexError(f"Case index {case_id} out of range (0-{len(all_ids) - 1})")
        resolved_case_id = all_ids[case_id]
    else:
        resolved_case_id = case_id

    # Get case files
    case_files = dataset.get_case(resolved_case_id)

    # 2. Stage Files
    # Use a temp dir for staging if output_dir not provided, or a subdir of output_dir
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        staging_root = output_dir / "staging" / resolved_case_id
        results_dir = output_dir / resolved_case_id
    else:
        # If no output dir, we create a temp dir that persists (unless cleanup requested)
        # But wait, the user wants paths. If we use tempfile.TemporaryDirectory context,
        # it disappears. We should use mkdtemp or let stage_case handle it.
        # Let's use a temp dir for staging.
        base_temp = Path(tempfile.mkdtemp(prefix="deepisles_pipeline_"))
        staging_root = base_temp / "staging"
        results_dir = base_temp / "results"

    staged = stage_case_for_deepisles(case_files, staging_root)

    # 3. Run Inference
    inference_result = run_deepisles_on_folder(
        staged.input_dir,
        output_dir=results_dir,
        fast=fast,
        gpu=gpu,
    )

    # 4. Compute Metrics
    dice_score: float | None = None
    ground_truth = case_files.get("ground_truth")

    if compute_dice and ground_truth and ground_truth.exists():
        try:
            dice_score = metrics.compute_dice(inference_result.prediction_path, ground_truth)
        except Exception:
            logger.warning("Failed to compute Dice score for %s", resolved_case_id, exc_info=True)

    # 5. Cleanup (Optional)
    if cleanup_staging:
        shutil.rmtree(staging_root, ignore_errors=True)

    elapsed = time.time() - start_time

    return PipelineResult(
        case_id=resolved_case_id,
        input_files=case_files,
        staged_dir=staged.input_dir,
        prediction_mask=inference_result.prediction_path,
        ground_truth=ground_truth,
        dice_score=dice_score,
        elapsed_seconds=elapsed,
    )


def run_pipeline_on_batch(
    case_ids: Sequence[str | int],
    *,
    max_workers: int = 1,
    **kwargs: object,
) -> list[PipelineResult]:
    """
    Run pipeline on multiple cases.

    Note: Parallel execution requires multiple GPUs or sequential mode.
    Currently only sequential execution is implemented (max_workers is ignored).

    Args:
        case_ids: List of case identifiers or indices
        max_workers: Number of parallel workers (default 1 for sequential).
                     Currently ignored - reserved for future parallel support.
        **kwargs: Passed to run_pipeline_on_case

    Returns:
        List of PipelineResult, one per case
    """
    # Currently only sequential execution is supported.
    # max_workers is accepted for API compatibility but ignored.
    _ = max_workers

    results: list[PipelineResult] = []
    for case_id in case_ids:
        result = run_pipeline_on_case(case_id, **kwargs)  # type: ignore[arg-type]
        results.append(result)

    return results


def get_pipeline_summary(results: Sequence[PipelineResult]) -> PipelineSummary:
    """
    Compute summary statistics from multiple pipeline results.

    Returns:
        Summary with mean Dice, success rate, etc.
    """
    # Filter results with valid dice scores
    dice_scores = [r.dice_score for r in results if r.dice_score is not None]
    elapsed_times = [r.elapsed_seconds for r in results]

    num_cases = len(results)
    # We assume all passed results are "successful" runs (failed runs raise exceptions)
    num_successful = num_cases
    num_failed = 0

    if dice_scores:
        mean_dice = statistics.mean(dice_scores)
        std_dice = statistics.stdev(dice_scores) if len(dice_scores) > 1 else 0.0
        min_dice = min(dice_scores)
        max_dice = max(dice_scores)
    else:
        mean_dice = None
        std_dice = None
        min_dice = None
        max_dice = None

    mean_elapsed = statistics.mean(elapsed_times) if elapsed_times else 0.0

    return PipelineSummary(
        num_cases=num_cases,
        num_successful=num_successful,
        num_failed=num_failed,
        mean_dice=mean_dice,
        std_dice=std_dice,
        min_dice=min_dice,
        max_dice=max_dice,
        mean_elapsed_seconds=mean_elapsed,
    )
