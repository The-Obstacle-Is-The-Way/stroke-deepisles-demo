# phase 3: end-to-end pipeline (no ui)

## purpose

Tie together Phase 1 (data loading) and Phase 2 (DeepISLES inference) into a cohesive pipeline. At the end of this phase, we can run stroke segmentation on any case from ISLES24-MR-Lite with a single function call.

## deliverables

- [ ] `src/stroke_deepisles_demo/pipeline.py` - Main orchestration
- [ ] `src/stroke_deepisles_demo/metrics.py` - Optional Dice computation
- [ ] CLI entry point for testing
- [ ] Unit tests with full mocking
- [ ] Integration test for complete flow

## vertical slice outcome

After this phase, you can run:

```python
from stroke_deepisles_demo.pipeline import run_pipeline_on_case

# Run segmentation on a specific case
result = run_pipeline_on_case("sub-001")

print(f"Input DWI: {result.input_files.dwi}")
print(f"Input ADC: {result.input_files.adc}")
print(f"Prediction: {result.prediction_mask}")
print(f"Ground truth: {result.ground_truth}")
print(f"Dice score: {result.dice_score:.3f}")  # if computed
```

Or via CLI:

```bash
uv run stroke-demo run --case sub-001 --fast
uv run stroke-demo run --index 0 --output ./results
uv run stroke-demo list  # List all available cases
```

## module structure

```
src/stroke_deepisles_demo/
├── pipeline.py          # Main orchestration
├── metrics.py           # Dice score computation
└── cli.py               # CLI entry point (optional)
```

## interfaces and types

### `pipeline.py`

```python
"""End-to-end pipeline orchestration."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from stroke_deepisles_demo.core.config import settings
from stroke_deepisles_demo.core.types import CaseFiles, InferenceResult
from stroke_deepisles_demo.data import CaseAdapter, load_isles_dataset, stage_case_for_deepisles
from stroke_deepisles_demo.inference import run_deepisles_on_folder


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

    This function:
    1. Loads the case from HuggingFace Hub (or cache)
    2. Stages NIfTI files with DeepISLES-expected naming
    3. Runs DeepISLES Docker container
    4. Optionally computes Dice score against ground truth
    5. Returns all paths and metrics

    Args:
        case_id: Case identifier (string) or index (int)
        dataset_id: HF dataset ID (default from settings)
        output_dir: Directory for results (default: temp dir)
        fast: Use SEALS-only mode (ISLES'22 winner, DWI+ADC only, no FLAIR needed)
        gpu: Use GPU acceleration
        compute_dice: Compute Dice score if ground truth available
        cleanup_staging: Remove staging directory after inference

    Returns:
        PipelineResult with all paths and optional metrics

    Raises:
        DataLoadError: If case cannot be loaded
        MissingInputError: If required files missing
        DeepISLESError: If inference fails

    Example:
        >>> result = run_pipeline_on_case("sub-001", fast=True)
        >>> print(f"Dice: {result.dice_score:.3f}")
    """
    ...


def run_pipeline_on_batch(
    case_ids: list[str | int],
    *,
    max_workers: int = 1,
    **kwargs,
) -> list[PipelineResult]:
    """
    Run pipeline on multiple cases.

    Note: Parallel execution requires multiple GPUs or sequential mode.

    Args:
        case_ids: List of case identifiers or indices
        max_workers: Number of parallel workers (default 1 for sequential)
        **kwargs: Passed to run_pipeline_on_case

    Returns:
        List of PipelineResult, one per case
    """
    ...


def get_pipeline_summary(results: list[PipelineResult]) -> PipelineSummary:
    """
    Compute summary statistics from multiple pipeline results.

    Returns:
        Summary with mean Dice, success rate, etc.
    """
    ...


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


# Internal helper
def _load_or_get_adapter(
    dataset_id: str | None = None,
    cache: dict | None = None,
) -> CaseAdapter:
    """Load dataset and return adapter, using cache if available."""
    ...
```

### `metrics.py`

```python
"""Metrics for evaluating segmentation quality."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
from numpy.typing import NDArray


def compute_dice(
    prediction: Path | NDArray[np.float64],
    ground_truth: Path | NDArray[np.float64],
    *,
    threshold: float = 0.5,
) -> float:
    """
    Compute Dice similarity coefficient between prediction and ground truth.

    Dice = 2 * |P ∩ G| / (|P| + |G|)

    Args:
        prediction: Path to NIfTI file or numpy array
        ground_truth: Path to NIfTI file or numpy array
        threshold: Threshold for binarization (if needed)

    Returns:
        Dice coefficient in [0, 1]

    Raises:
        ValueError: If shapes don't match
    """
    ...


def compute_volume_ml(
    mask: Path | NDArray[np.float64],
    voxel_size_mm: tuple[float, float, float] | None = None,
) -> float:
    """
    Compute lesion volume in milliliters.

    Args:
        mask: Path to NIfTI file or numpy array
        voxel_size_mm: Voxel dimensions in mm (read from NIfTI if None)

    Returns:
        Volume in milliliters (mL)
    """
    ...


def load_nifti_as_array(path: Path) -> tuple[NDArray[np.float64], tuple[float, ...]]:
    """
    Load NIfTI file and return data array with voxel dimensions.

    Returns:
        Tuple of (data_array, voxel_sizes_mm)
    """
    ...
```

### `cli.py` (optional)

```python
"""Command-line interface for stroke-deepisles-demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="stroke-demo",
        description="Run DeepISLES stroke segmentation on HF datasets",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    list_parser = subparsers.add_parser("list", help="List available cases")
    list_parser.add_argument(
        "--dataset", default=None, help="HF dataset ID"
    )

    # Run command
    run_parser = subparsers.add_parser("run", help="Run segmentation")
    run_parser.add_argument(
        "--case", type=str, help="Case ID (e.g., sub-001)"
    )
    run_parser.add_argument(
        "--index", type=int, help="Case index (alternative to --case)"
    )
    run_parser.add_argument(
        "--output", type=Path, default=None, help="Output directory"
    )
    run_parser.add_argument(
        "--fast", action="store_true", default=True, help="Use fast mode"
    )
    run_parser.add_argument(
        "--no-gpu", action="store_true", help="Disable GPU"
    )

    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args)
    elif args.command == "run":
        return cmd_run(args)

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Handle 'list' command."""
    ...


def cmd_run(args: argparse.Namespace) -> int:
    """Handle 'run' command."""
    ...


if __name__ == "__main__":
    sys.exit(main())
```

### pyproject.toml addition for CLI

```toml
[project.scripts]
stroke-demo = "stroke_deepisles_demo.cli:main"
```

## tdd plan

### test file structure

```
tests/
├── test_pipeline.py         # Pipeline orchestration tests
├── test_metrics.py          # Metrics computation tests
└── test_cli.py              # CLI tests (optional)
```

### tests to write first (TDD order)

#### 1. `tests/test_metrics.py` - Pure functions, no mocks needed

```python
"""Tests for metrics module."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from stroke_deepisles_demo.metrics import (
    compute_dice,
    compute_volume_ml,
    load_nifti_as_array,
)


class TestComputeDice:
    """Tests for compute_dice."""

    def test_identical_masks_return_one(self) -> None:
        """Dice of identical masks is 1.0."""
        mask = np.array([[[1, 1, 0], [0, 1, 0], [0, 0, 1]]])

        dice = compute_dice(mask, mask)

        assert dice == 1.0

    def test_no_overlap_returns_zero(self) -> None:
        """Dice of non-overlapping masks is 0.0."""
        pred = np.array([[[1, 1, 0], [0, 0, 0], [0, 0, 0]]])
        gt = np.array([[[0, 0, 0], [0, 0, 0], [0, 0, 1]]])

        dice = compute_dice(pred, gt)

        assert dice == 0.0

    def test_partial_overlap(self) -> None:
        """Dice with partial overlap is between 0 and 1."""
        pred = np.array([[[1, 1, 0], [0, 0, 0], [0, 0, 0]]])
        gt = np.array([[[1, 0, 0], [0, 0, 0], [0, 0, 0]]])

        dice = compute_dice(pred, gt)

        # Overlap: 1, Pred: 2, GT: 1 -> Dice = 2*1 / (2+1) = 0.667
        assert 0.6 < dice < 0.7

    def test_empty_masks_return_one(self) -> None:
        """Dice of two empty masks is 1.0 (both agree on nothing)."""
        empty = np.zeros((10, 10, 10))

        dice = compute_dice(empty, empty)

        assert dice == 1.0

    def test_accepts_file_paths(self, temp_dir: Path) -> None:
        """Can compute Dice from NIfTI file paths."""
        mask = np.array([[[1, 1, 0], [0, 1, 0], [0, 0, 1]]]).astype(np.float32)
        img = nib.Nifti1Image(mask, np.eye(4))

        pred_path = temp_dir / "pred.nii.gz"
        gt_path = temp_dir / "gt.nii.gz"
        nib.save(img, pred_path)
        nib.save(img, gt_path)

        dice = compute_dice(pred_path, gt_path)

        assert dice == 1.0

    def test_shape_mismatch_raises(self) -> None:
        """Raises ValueError if shapes don't match."""
        pred = np.zeros((10, 10, 10))
        gt = np.zeros((10, 10, 5))

        with pytest.raises(ValueError, match="shape"):
            compute_dice(pred, gt)


class TestComputeVolumeMl:
    """Tests for compute_volume_ml."""

    def test_computes_volume_from_voxel_size(self) -> None:
        """Volume computed correctly from voxel dimensions."""
        # 10x10x10 = 1000 voxels of size 1mm^3 each = 1000mm^3 = 1mL
        mask = np.ones((10, 10, 10))

        volume = compute_volume_ml(mask, voxel_size_mm=(1.0, 1.0, 1.0))

        assert volume == pytest.approx(1.0, rel=0.01)

    def test_reads_voxel_size_from_nifti(self, temp_dir: Path) -> None:
        """Reads voxel size from NIfTI header."""
        mask = np.ones((10, 10, 10)).astype(np.float32)
        # Affine with 2mm voxels
        affine = np.diag([2.0, 2.0, 2.0, 1.0])
        img = nib.Nifti1Image(mask, affine)

        path = temp_dir / "mask.nii.gz"
        nib.save(img, path)

        # 1000 voxels * 8mm^3 = 8000mm^3 = 8mL
        volume = compute_volume_ml(path)

        assert volume == pytest.approx(8.0, rel=0.01)


class TestLoadNiftiAsArray:
    """Tests for load_nifti_as_array."""

    def test_returns_array_and_voxel_sizes(self, temp_dir: Path) -> None:
        """Returns data array and voxel dimensions."""
        data = np.random.rand(10, 10, 10).astype(np.float32)
        affine = np.diag([1.5, 1.5, 2.0, 1.0])
        img = nib.Nifti1Image(data, affine)

        path = temp_dir / "test.nii.gz"
        nib.save(img, path)

        arr, voxels = load_nifti_as_array(path)

        assert arr.shape == (10, 10, 10)
        assert voxels == pytest.approx((1.5, 1.5, 2.0), rel=0.01)
```

#### 2. `tests/test_pipeline.py` - Full orchestration with mocks

```python
"""Tests for pipeline orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.types import CaseFiles
from stroke_deepisles_demo.pipeline import (
    PipelineResult,
    PipelineSummary,
    get_pipeline_summary,
    run_pipeline_on_case,
)


class TestRunPipelineOnCase:
    """Tests for run_pipeline_on_case."""

    @pytest.fixture
    def mock_dependencies(self, temp_dir: Path):
        """Mock all external dependencies."""
        with patch(
            "stroke_deepisles_demo.pipeline.load_isles_dataset"
        ) as mock_load, patch(
            "stroke_deepisles_demo.pipeline.CaseAdapter"
        ) as mock_adapter_cls, patch(
            "stroke_deepisles_demo.pipeline.stage_case_for_deepisles"
        ) as mock_stage, patch(
            "stroke_deepisles_demo.pipeline.run_deepisles_on_folder"
        ) as mock_inference, patch(
            "stroke_deepisles_demo.pipeline.compute_dice"
        ) as mock_dice:
            # Configure mocks
            mock_adapter = MagicMock()
            mock_adapter.get_case.return_value = CaseFiles(
                dwi=temp_dir / "dwi.nii.gz",
                adc=temp_dir / "adc.nii.gz",
                flair=None,
                ground_truth=temp_dir / "gt.nii.gz",
            )
            mock_adapter_cls.return_value = mock_adapter

            mock_stage.return_value = MagicMock(
                input_dir=temp_dir / "staged",
                dwi_path=temp_dir / "staged" / "dwi.nii.gz",
                adc_path=temp_dir / "staged" / "adc.nii.gz",
                flair_path=None,
            )

            mock_inference.return_value = MagicMock(
                prediction_path=temp_dir / "results" / "pred.nii.gz",
                elapsed_seconds=10.5,
            )

            mock_dice.return_value = 0.85

            yield {
                "load": mock_load,
                "adapter_cls": mock_adapter_cls,
                "adapter": mock_adapter,
                "stage": mock_stage,
                "inference": mock_inference,
                "dice": mock_dice,
            }

    def test_returns_pipeline_result(self, mock_dependencies, temp_dir) -> None:
        """Returns PipelineResult with expected fields."""
        result = run_pipeline_on_case("sub-001")

        assert isinstance(result, PipelineResult)
        assert result.case_id == "sub-001"

    def test_loads_case_from_adapter(self, mock_dependencies, temp_dir) -> None:
        """Loads case using CaseAdapter."""
        run_pipeline_on_case("sub-001")

        mock_dependencies["adapter"].get_case.assert_called_once_with("sub-001")

    def test_stages_files_for_deepisles(self, mock_dependencies, temp_dir) -> None:
        """Stages files with correct naming."""
        run_pipeline_on_case("sub-001")

        mock_dependencies["stage"].assert_called_once()

    def test_runs_deepisles_inference(self, mock_dependencies, temp_dir) -> None:
        """Runs DeepISLES on staged directory."""
        run_pipeline_on_case("sub-001", fast=True, gpu=False)

        mock_dependencies["inference"].assert_called_once()
        call_kwargs = mock_dependencies["inference"].call_args.kwargs
        assert call_kwargs.get("fast") is True
        assert call_kwargs.get("gpu") is False

    def test_computes_dice_when_ground_truth_available(
        self, mock_dependencies, temp_dir
    ) -> None:
        """Computes Dice score when ground truth is available."""
        result = run_pipeline_on_case("sub-001", compute_dice=True)

        mock_dependencies["dice"].assert_called_once()
        assert result.dice_score == 0.85

    def test_skips_dice_when_disabled(self, mock_dependencies, temp_dir) -> None:
        """Skips Dice computation when compute_dice=False."""
        result = run_pipeline_on_case("sub-001", compute_dice=False)

        mock_dependencies["dice"].assert_not_called()
        assert result.dice_score is None

    def test_handles_missing_ground_truth(self, mock_dependencies, temp_dir) -> None:
        """Handles cases without ground truth gracefully."""
        # Modify mock to return no ground truth
        mock_dependencies["adapter"].get_case.return_value = CaseFiles(
            dwi=temp_dir / "dwi.nii.gz",
            adc=temp_dir / "adc.nii.gz",
            flair=None,
            ground_truth=None,
        )

        result = run_pipeline_on_case("sub-001", compute_dice=True)

        assert result.dice_score is None
        assert result.ground_truth is None

    def test_accepts_integer_index(self, mock_dependencies, temp_dir) -> None:
        """Accepts integer index as case identifier."""
        mock_dependencies["adapter"].get_case_by_index.return_value = (
            "sub-001",
            CaseFiles(
                dwi=temp_dir / "dwi.nii.gz",
                adc=temp_dir / "adc.nii.gz",
                flair=None,
                ground_truth=None,
            ),
        )

        result = run_pipeline_on_case(0)

        assert result.case_id == "sub-001"


class TestGetPipelineSummary:
    """Tests for get_pipeline_summary."""

    def test_computes_mean_dice(self) -> None:
        """Computes mean Dice from results."""
        results = [
            MagicMock(dice_score=0.8, elapsed_seconds=10),
            MagicMock(dice_score=0.9, elapsed_seconds=12),
            MagicMock(dice_score=0.7, elapsed_seconds=8),
        ]

        summary = get_pipeline_summary(results)

        assert summary.mean_dice == pytest.approx(0.8, rel=0.01)

    def test_handles_none_dice_scores(self) -> None:
        """Handles results with None Dice scores."""
        results = [
            MagicMock(dice_score=0.8, elapsed_seconds=10),
            MagicMock(dice_score=None, elapsed_seconds=12),
            MagicMock(dice_score=0.7, elapsed_seconds=8),
        ]

        summary = get_pipeline_summary(results)

        # Mean of 0.8 and 0.7 only
        assert summary.mean_dice == pytest.approx(0.75, rel=0.01)

    def test_counts_successful_and_failed(self) -> None:
        """Counts successful and failed runs."""
        results = [
            MagicMock(dice_score=0.8, elapsed_seconds=10),
            MagicMock(dice_score=None, elapsed_seconds=0),  # Failed
        ]

        summary = get_pipeline_summary(results)

        assert summary.num_cases == 2
        assert summary.num_successful == 1
        assert summary.num_failed == 1


@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for full pipeline."""

    @pytest.mark.slow
    def test_run_on_real_case(self) -> None:
        """Run pipeline on actual ISLES24-MR-Lite case."""
        # Requires: network, Docker, DeepISLES image
        # Run with: pytest -m "integration and slow"

        result = run_pipeline_on_case(
            0,  # First case
            fast=True,
            gpu=False,
            compute_dice=True,
        )

        assert result.prediction_mask.exists()
        assert 0 <= result.dice_score <= 1
```

### what to mock

- `load_isles_dataset` - Avoid network calls
- `CaseAdapter` - Return synthetic CaseFiles
- `stage_case_for_deepisles` - Return mock staged paths
- `run_deepisles_on_folder` - Avoid Docker
- `compute_dice` - Return fixed value for deterministic tests

### what to test for real

- Dice computation (pure NumPy)
- Volume computation (pure NumPy + nibabel)
- NIfTI loading
- Integration: full pipeline on real data

## "done" criteria

Phase 3 is complete when:

1. All unit tests pass: `uv run pytest tests/test_pipeline.py tests/test_metrics.py -v`
2. Dice computation is correct for known test cases
3. Pipeline orchestrates all components correctly
4. CLI works: `uv run stroke-demo list` and `uv run stroke-demo run --index 0`
5. Integration test passes: `uv run pytest -m "integration and slow"`
6. Type checking passes: `uv run mypy src/stroke_deepisles_demo/pipeline.py src/stroke_deepisles_demo/metrics.py`
7. Code coverage for pipeline module > 80%

## implementation notes

- Use dataclasses for results (immutable, typed)
- Consider caching the loaded dataset in module-level variable
- Dice should handle edge cases (empty masks, shape mismatches)
- CLI is optional but useful for manual testing
- Batch processing is sequential by default (GPU constraint)
