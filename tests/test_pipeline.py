"""Tests for pipeline orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.types import CaseFiles
from stroke_deepisles_demo.pipeline import (
    PipelineResult,
    get_pipeline_summary,
    run_pipeline_on_batch,
    run_pipeline_on_case,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class TestRunPipelineOnCase:
    """Tests for run_pipeline_on_case."""

    @pytest.fixture
    def mock_dependencies(self, temp_dir: Path) -> Iterator[dict[str, MagicMock]]:
        """Mock all external dependencies."""
        with (
            patch("stroke_deepisles_demo.pipeline.load_isles_dataset") as mock_load,
            patch("stroke_deepisles_demo.pipeline.stage_case_for_deepisles") as mock_stage,
            patch("stroke_deepisles_demo.pipeline.run_deepisles_on_folder") as mock_inference,
            patch("stroke_deepisles_demo.metrics.compute_dice") as mock_dice,
        ):
            # Configure mocks
            mock_dataset = MagicMock()

            # Mock paths that "exist"
            dwi_path = MagicMock(spec=Path)
            dwi_path.exists.return_value = True
            adc_path = MagicMock(spec=Path)
            adc_path.exists.return_value = True
            gt_path = MagicMock(spec=Path)
            gt_path.exists.return_value = True

            mock_dataset.get_case.return_value = CaseFiles(
                dwi=dwi_path,
                adc=adc_path,
                ground_truth=gt_path,
                # flair omitted
            )
            mock_load.return_value = mock_dataset

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
                "dataset": mock_dataset,
                "stage": mock_stage,
                "inference": mock_inference,
                "dice": mock_dice,
            }

    def test_returns_pipeline_result(
        self, mock_dependencies: dict[str, MagicMock], temp_dir: Path
    ) -> None:
        """Returns PipelineResult with expected fields."""
        _ = mock_dependencies  # explicit usage
        _ = temp_dir
        result = run_pipeline_on_case("sub-001")

        assert isinstance(result, PipelineResult)
        assert result.case_id == "sub-001"

    def test_loads_case_from_dataset(
        self,
        mock_dependencies: dict[str, MagicMock],
        temp_dir: Path,  # noqa: ARG002
    ) -> None:
        """Loads case using dataset."""
        run_pipeline_on_case("sub-001")

        mock_dependencies["dataset"].get_case.assert_called_once_with("sub-001")

    def test_stages_files_for_deepisles(
        self,
        mock_dependencies: dict[str, MagicMock],
        temp_dir: Path,  # noqa: ARG002
    ) -> None:
        """Stages files with correct naming."""
        run_pipeline_on_case("sub-001")

        mock_dependencies["stage"].assert_called_once()

    def test_runs_deepisles_inference(
        self,
        mock_dependencies: dict[str, MagicMock],
        temp_dir: Path,  # noqa: ARG002
    ) -> None:
        """Runs DeepISLES on staged directory."""
        run_pipeline_on_case("sub-001", fast=True, gpu=False)

        mock_dependencies["inference"].assert_called_once()
        call_kwargs = mock_dependencies["inference"].call_args.kwargs
        assert call_kwargs.get("fast") is True
        assert call_kwargs.get("gpu") is False

    def test_computes_dice_when_ground_truth_available(
        self,
        mock_dependencies: dict[str, MagicMock],
        temp_dir: Path,  # noqa: ARG002
    ) -> None:
        """Computes Dice score when ground truth is available."""
        result = run_pipeline_on_case("sub-001", compute_dice=True)

        mock_dependencies["dice"].assert_called_once()
        assert result.dice_score == 0.85

    def test_skips_dice_when_disabled(
        self,
        mock_dependencies: dict[str, MagicMock],
        temp_dir: Path,  # noqa: ARG002
    ) -> None:
        """Skips Dice computation when compute_dice=False."""
        result = run_pipeline_on_case("sub-001", compute_dice=False)

        mock_dependencies["dice"].assert_not_called()
        assert result.dice_score is None

    def test_handles_missing_ground_truth(
        self,
        mock_dependencies: dict[str, MagicMock],
        temp_dir: Path,  # noqa: ARG002
    ) -> None:
        """Handles cases without ground truth gracefully."""
        # Modify mock to return no ground truth
        dwi = MagicMock(spec=Path)
        adc = MagicMock(spec=Path)
        mock_dependencies["dataset"].get_case.return_value = CaseFiles(
            dwi=dwi,
            adc=adc,
            # ground_truth omitted
        )

        result = run_pipeline_on_case("sub-001", compute_dice=True)

        assert result.dice_score is None
        assert result.ground_truth is None

    def test_accepts_integer_index(
        self,
        mock_dependencies: dict[str, MagicMock],
        temp_dir: Path,  # noqa: ARG002
    ) -> None:
        """Accepts integer index as case identifier."""
        mock_dependencies["dataset"].list_case_ids.return_value = ["sub-001"]

        result = run_pipeline_on_case(0)

        assert result.case_id == "sub-001"


class TestGetPipelineSummary:
    """Tests for get_pipeline_summary."""

    def test_computes_mean_dice(self) -> None:
        """Computes mean Dice from results."""
        from types import SimpleNamespace

        results = [
            SimpleNamespace(dice_score=0.8, elapsed_seconds=10.0),
            SimpleNamespace(dice_score=0.9, elapsed_seconds=12.0),
            SimpleNamespace(dice_score=0.7, elapsed_seconds=8.0),
        ]

        summary = get_pipeline_summary(results)  # type: ignore

        assert summary.mean_dice == pytest.approx(0.8, rel=0.01)

    def test_handles_none_dice_scores(self) -> None:
        """Handles results with None Dice scores."""
        from types import SimpleNamespace

        results = [
            SimpleNamespace(dice_score=0.8, elapsed_seconds=10.0),
            SimpleNamespace(dice_score=None, elapsed_seconds=12.0),
            SimpleNamespace(dice_score=0.7, elapsed_seconds=8.0),
        ]

        summary = get_pipeline_summary(results)  # type: ignore

        # Mean of 0.8 and 0.7 only
        assert summary.mean_dice == pytest.approx(0.75, rel=0.01)

    def test_counts_successful_and_failed(self) -> None:
        """Counts successful and failed runs."""
        from types import SimpleNamespace

        # Assuming current implementation counts all as successful
        results = [
            SimpleNamespace(dice_score=0.8, elapsed_seconds=10.0),
            SimpleNamespace(dice_score=None, elapsed_seconds=0.0),
        ]

        summary = get_pipeline_summary(results)  # type: ignore

        assert summary.num_cases == 2
        assert summary.num_successful == 2
        assert summary.num_failed == 0


class TestRunPipelineOnBatch:
    """Tests for run_pipeline_on_batch."""

    def test_runs_multiple_cases(self) -> None:
        """Runs pipeline on multiple cases sequentially."""
        with patch("stroke_deepisles_demo.pipeline.run_pipeline_on_case") as mock_run:
            mock_run.side_effect = [
                PipelineResult(
                    case_id="sub-001",
                    input_files=MagicMock(),
                    staged_dir=MagicMock(),
                    prediction_mask=MagicMock(),
                    ground_truth=None,
                    dice_score=0.8,
                    elapsed_seconds=10.0,
                ),
                PipelineResult(
                    case_id="sub-002",
                    input_files=MagicMock(),
                    staged_dir=MagicMock(),
                    prediction_mask=MagicMock(),
                    ground_truth=None,
                    dice_score=0.9,
                    elapsed_seconds=12.0,
                ),
            ]

            results = run_pipeline_on_batch(["sub-001", "sub-002"], fast=True, gpu=False)

            assert len(results) == 2
            assert results[0].case_id == "sub-001"
            assert results[1].case_id == "sub-002"
            assert mock_run.call_count == 2

    def test_passes_kwargs_to_each_call(self) -> None:
        """Passes kwargs to each run_pipeline_on_case call."""
        with patch("stroke_deepisles_demo.pipeline.run_pipeline_on_case") as mock_run:
            mock_run.return_value = PipelineResult(
                case_id="sub-001",
                input_files=MagicMock(),
                staged_dir=MagicMock(),
                prediction_mask=MagicMock(),
                ground_truth=None,
                dice_score=0.8,
                elapsed_seconds=10.0,
            )

            run_pipeline_on_batch(["sub-001"], fast=False, gpu=True, compute_dice=False)

            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs.get("fast") is False
            assert call_kwargs.get("gpu") is True
            assert call_kwargs.get("compute_dice") is False


@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for full pipeline."""

    @pytest.mark.slow
    def test_run_on_real_case(self, temp_dir: Path) -> None:
        """Run pipeline on actual ISLES24-MR-Lite case."""
        # Requires: network, Docker, DeepISLES image
        # Run with: pytest -m "integration and slow"

        from stroke_deepisles_demo.inference.docker import check_docker_available

        if not check_docker_available():
            pytest.skip("Docker not available")

        result = run_pipeline_on_case(
            0,  # First case
            fast=True,
            gpu=False,
            compute_dice=True,
            output_dir=temp_dir / "pipeline_test_output",
        )

        assert result.prediction_mask.exists()
        # Dice might be None if no ground truth, but ISLES24 has masks
        # We asserted earlier that phase 1 data has masks.
        if result.ground_truth:
            assert result.dice_score is not None
            assert 0 <= result.dice_score <= 1
