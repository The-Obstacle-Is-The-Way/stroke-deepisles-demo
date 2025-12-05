"""Tests for DeepISLES wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.exceptions import DeepISLESError, MissingInputError
from stroke_deepisles_demo.inference.deepisles import (
    DeepISLESResult,
    find_prediction_mask,
    run_deepisles_on_folder,
    validate_input_folder,
)


class TestValidateInputFolder:
    """Tests for validate_input_folder."""

    def test_succeeds_with_required_files(self, temp_dir: Path) -> None:
        """Returns paths when required files exist."""
        (temp_dir / "dwi.nii.gz").touch()
        (temp_dir / "adc.nii.gz").touch()

        dwi, adc, flair = validate_input_folder(temp_dir)

        assert dwi == temp_dir / "dwi.nii.gz"
        assert adc == temp_dir / "adc.nii.gz"
        assert flair is None

    def test_includes_flair_when_present(self, temp_dir: Path) -> None:
        """Returns FLAIR path when present."""
        (temp_dir / "dwi.nii.gz").touch()
        (temp_dir / "adc.nii.gz").touch()
        (temp_dir / "flair.nii.gz").touch()

        _dwi, _adc, flair = validate_input_folder(temp_dir)

        assert flair == temp_dir / "flair.nii.gz"

    def test_raises_when_dwi_missing(self, temp_dir: Path) -> None:
        """Raises MissingInputError when DWI is missing."""
        (temp_dir / "adc.nii.gz").touch()

        with pytest.raises(MissingInputError, match="dwi"):
            validate_input_folder(temp_dir)

    def test_raises_when_adc_missing(self, temp_dir: Path) -> None:
        """Raises MissingInputError when ADC is missing."""
        (temp_dir / "dwi.nii.gz").touch()

        with pytest.raises(MissingInputError, match="adc"):
            validate_input_folder(temp_dir)


class TestFindPredictionMask:
    """Tests for find_prediction_mask."""

    def test_finds_prediction_file(self, temp_dir: Path) -> None:
        """Finds prediction.nii.gz in output directory."""
        results_dir = temp_dir / "results"
        results_dir.mkdir()
        pred_file = results_dir / "prediction.nii.gz"
        pred_file.touch()

        result = find_prediction_mask(temp_dir)

        assert result == pred_file

    def test_finds_alternate_name(self, temp_dir: Path) -> None:
        """Finds alternate named prediction files."""
        results_dir = temp_dir / "results"
        results_dir.mkdir()
        pred_file = results_dir / "pred.nii.gz"
        pred_file.touch()

        result = find_prediction_mask(temp_dir)

        assert result == pred_file

    def test_falls_back_to_any_nifti(self, temp_dir: Path) -> None:
        """Falls back to any .nii.gz file if standard names not found."""
        results_dir = temp_dir / "results"
        results_dir.mkdir()
        pred_file = results_dir / "some_output.nii.gz"
        pred_file.touch()

        result = find_prediction_mask(temp_dir)

        assert result == pred_file

    def test_raises_when_no_prediction(self, temp_dir: Path) -> None:
        """Raises DeepISLESError when no prediction found."""
        results_dir = temp_dir / "results"
        results_dir.mkdir()

        with pytest.raises(DeepISLESError, match="prediction"):
            find_prediction_mask(temp_dir)

    def test_raises_when_results_dir_missing(self, temp_dir: Path) -> None:
        """Raises DeepISLESError when results directory missing."""
        with pytest.raises(DeepISLESError, match="prediction"):
            find_prediction_mask(temp_dir)


class TestRunDeepIslesOnFolder:
    """Tests for run_deepisles_on_folder."""

    @pytest.fixture
    def valid_input_dir(self, temp_dir: Path) -> Path:
        """Create a valid input directory with required files."""
        (temp_dir / "dwi.nii.gz").touch()
        (temp_dir / "adc.nii.gz").touch()
        return temp_dir

    def test_validates_input_files(self, temp_dir: Path) -> None:
        """Validates input files before running Docker."""
        # Missing required files
        with pytest.raises(MissingInputError):
            run_deepisles_on_folder(temp_dir)

    def test_calls_docker_with_correct_image(self, valid_input_dir: Path) -> None:
        """Calls Docker with DeepISLES image."""
        with patch("stroke_deepisles_demo.inference.deepisles.run_container") as mock_run:
            mock_run.return_value = MagicMock(exit_code=0, stdout="", stderr="")
            with (
                patch(
                    "stroke_deepisles_demo.inference.deepisles.ensure_gpu_available_if_requested"
                ),
                patch(
                    "stroke_deepisles_demo.inference.deepisles.find_prediction_mask"
                ) as mock_find,
            ):
                mock_find.return_value = valid_input_dir / "results" / "pred.nii.gz"
                run_deepisles_on_folder(valid_input_dir)

            # Check image name
            call_args = mock_run.call_args
            assert call_args.args[0] == "isleschallenge/deepisles"

    def test_passes_fast_flag(self, valid_input_dir: Path) -> None:
        """Passes --fast True when fast=True."""
        with patch("stroke_deepisles_demo.inference.deepisles.run_container") as mock_run:
            mock_run.return_value = MagicMock(exit_code=0, stdout="", stderr="")
            with (
                patch(
                    "stroke_deepisles_demo.inference.deepisles.ensure_gpu_available_if_requested"
                ),
                patch(
                    "stroke_deepisles_demo.inference.deepisles.find_prediction_mask"
                ) as mock_find,
            ):
                mock_find.return_value = valid_input_dir / "results" / "pred.nii.gz"

                run_deepisles_on_folder(valid_input_dir, fast=True)

            # Check --fast in command
            call_kwargs = mock_run.call_args.kwargs
            command = call_kwargs.get("command", [])
            assert "--fast" in command
            assert "True" in command

    def test_includes_flair_when_present(self, valid_input_dir: Path) -> None:
        """Includes FLAIR in command when present."""
        (valid_input_dir / "flair.nii.gz").touch()

        with patch("stroke_deepisles_demo.inference.deepisles.run_container") as mock_run:
            mock_run.return_value = MagicMock(exit_code=0, stdout="", stderr="")
            with (
                patch(
                    "stroke_deepisles_demo.inference.deepisles.ensure_gpu_available_if_requested"
                ),
                patch(
                    "stroke_deepisles_demo.inference.deepisles.find_prediction_mask"
                ) as mock_find,
            ):
                mock_find.return_value = valid_input_dir / "results" / "pred.nii.gz"

                run_deepisles_on_folder(valid_input_dir)

            call_kwargs = mock_run.call_args.kwargs
            command = call_kwargs.get("command", [])
            assert "--flair_file_name" in command
            assert "flair.nii.gz" in command

    def test_raises_on_docker_failure(self, valid_input_dir: Path) -> None:
        """Raises DeepISLESError when Docker returns non-zero."""
        with patch("stroke_deepisles_demo.inference.deepisles.run_container") as mock_run:
            mock_run.return_value = MagicMock(exit_code=1, stdout="", stderr="Segmentation fault")
            with (
                patch(
                    "stroke_deepisles_demo.inference.deepisles.ensure_gpu_available_if_requested"
                ),
                pytest.raises(DeepISLESError, match="failed"),
            ):
                run_deepisles_on_folder(valid_input_dir)

    def test_returns_result_with_prediction_path(self, valid_input_dir: Path) -> None:
        """Returns DeepISLESResult with prediction path."""
        with patch("stroke_deepisles_demo.inference.deepisles.run_container") as mock_run:
            mock_run.return_value = MagicMock(
                exit_code=0, stdout="", stderr="", elapsed_seconds=10.0
            )
            with (
                patch(
                    "stroke_deepisles_demo.inference.deepisles.ensure_gpu_available_if_requested"
                ),
                patch(
                    "stroke_deepisles_demo.inference.deepisles.find_prediction_mask"
                ) as mock_find,
            ):
                expected_path = valid_input_dir / "results" / "prediction.nii.gz"
                mock_find.return_value = expected_path

                result = run_deepisles_on_folder(valid_input_dir)

            assert isinstance(result, DeepISLESResult)
            assert result.prediction_path == expected_path

    def test_passes_volume_mounts(self, valid_input_dir: Path, temp_dir: Path) -> None:
        """Passes correct volume mounts to Docker."""
        # Create a separate output directory
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        with patch("stroke_deepisles_demo.inference.deepisles.run_container") as mock_run:
            mock_run.return_value = MagicMock(exit_code=0, stdout="", stderr="")
            with (
                patch(
                    "stroke_deepisles_demo.inference.deepisles.ensure_gpu_available_if_requested"
                ),
                patch(
                    "stroke_deepisles_demo.inference.deepisles.find_prediction_mask"
                ) as mock_find,
            ):
                mock_find.return_value = output_dir / "results" / "pred.nii.gz"

                run_deepisles_on_folder(valid_input_dir, output_dir=output_dir)

            call_kwargs = mock_run.call_args.kwargs
            volumes = call_kwargs.get("volumes", {})
            # Should have input and output mounts (2 separate directories)
            assert len(volumes) == 2
            # Values should be container paths
            assert "/input" in volumes.values()
            assert "/output" in volumes.values()


@pytest.mark.integration
@pytest.mark.slow
class TestDeepIslesIntegration:
    """Integration tests requiring real Docker and DeepISLES image."""

    def test_real_inference(self, synthetic_case_files: dict[str, object]) -> None:
        """Run actual DeepISLES inference on synthetic data."""
        # This test requires:
        # 1. Docker available
        # 2. isleschallenge/deepisles image pulled
        # 3. GPU (optional but recommended)
        #
        # Run with: pytest -m integration
        import tempfile

        from stroke_deepisles_demo.data.staging import stage_case_for_deepisles

        # Create a separate staging directory
        with tempfile.TemporaryDirectory() as staging_dir:
            # Stage the synthetic files to the new directory
            staged = stage_case_for_deepisles(
                synthetic_case_files,  # type: ignore[arg-type]
                Path(staging_dir),
            )

            # Run inference
            result = run_deepisles_on_folder(
                staged.input_dir,
                fast=True,
                gpu=False,  # Might not have GPU in CI
                timeout=600,
            )

            # Verify output exists
            assert result.prediction_path.exists()
