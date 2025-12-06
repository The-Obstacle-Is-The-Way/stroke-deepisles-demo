"""Tests for direct DeepISLES invocation module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from stroke_deepisles_demo.core.exceptions import DeepISLESError, MissingInputError
from stroke_deepisles_demo.inference.direct import (
    _find_prediction_mask,
    validate_input_files,
)


class TestValidateInputFiles:
    """Tests for validate_input_files."""

    def test_valid_files(self, tmp_path: Path) -> None:
        """Passes validation when required files exist."""
        dwi = tmp_path / "dwi.nii.gz"
        adc = tmp_path / "adc.nii.gz"
        dwi.touch()
        adc.touch()

        # Should not raise
        validate_input_files(dwi, adc)

    def test_valid_files_with_flair(self, tmp_path: Path) -> None:
        """Passes validation when all files including FLAIR exist."""
        dwi = tmp_path / "dwi.nii.gz"
        adc = tmp_path / "adc.nii.gz"
        flair = tmp_path / "flair.nii.gz"
        dwi.touch()
        adc.touch()
        flair.touch()

        # Should not raise
        validate_input_files(dwi, adc, flair)

    def test_missing_dwi(self, tmp_path: Path) -> None:
        """Raises MissingInputError when DWI file missing."""
        dwi = tmp_path / "dwi.nii.gz"
        adc = tmp_path / "adc.nii.gz"
        adc.touch()

        with pytest.raises(MissingInputError, match="DWI file not found"):
            validate_input_files(dwi, adc)

    def test_missing_adc(self, tmp_path: Path) -> None:
        """Raises MissingInputError when ADC file missing."""
        dwi = tmp_path / "dwi.nii.gz"
        adc = tmp_path / "adc.nii.gz"
        dwi.touch()

        with pytest.raises(MissingInputError, match="ADC file not found"):
            validate_input_files(dwi, adc)

    def test_missing_flair_when_specified(self, tmp_path: Path) -> None:
        """Raises MissingInputError when FLAIR specified but missing."""
        dwi = tmp_path / "dwi.nii.gz"
        adc = tmp_path / "adc.nii.gz"
        flair = tmp_path / "flair.nii.gz"
        dwi.touch()
        adc.touch()

        with pytest.raises(MissingInputError, match="FLAIR file not found"):
            validate_input_files(dwi, adc, flair)


class TestFindPredictionMask:
    """Tests for _find_prediction_mask."""

    def test_finds_prediction_in_results_dir(self, tmp_path: Path) -> None:
        """Finds prediction.nii.gz in results subdirectory."""
        results = tmp_path / "results"
        results.mkdir()
        pred = results / "prediction.nii.gz"
        pred.touch()

        found = _find_prediction_mask(tmp_path)
        assert found == pred

    def test_finds_alternative_names(self, tmp_path: Path) -> None:
        """Finds prediction with alternative naming patterns."""
        results = tmp_path / "results"
        results.mkdir()
        pred = results / "lesion_mask.nii.gz"
        pred.touch()

        found = _find_prediction_mask(tmp_path)
        assert found == pred

    def test_finds_in_output_dir_directly(self, tmp_path: Path) -> None:
        """Finds prediction directly in output directory."""
        pred = tmp_path / "prediction.nii.gz"
        pred.touch()

        found = _find_prediction_mask(tmp_path)
        assert found == pred

    def test_finds_any_nifti(self, tmp_path: Path) -> None:
        """Falls back to any NIfTI file if standard names not found."""
        results = tmp_path / "results"
        results.mkdir()
        pred = results / "custom_output.nii.gz"
        pred.touch()

        found = _find_prediction_mask(tmp_path)
        assert found == pred

    def test_excludes_input_files(self, tmp_path: Path) -> None:
        """Excludes DWI/ADC/FLAIR from fallback search."""
        # Only input files, no prediction
        (tmp_path / "dwi.nii.gz").touch()
        (tmp_path / "adc.nii.gz").touch()

        with pytest.raises(DeepISLESError, match="No prediction mask found"):
            _find_prediction_mask(tmp_path)

    def test_no_mask_found(self, tmp_path: Path) -> None:
        """Raises DeepISLESError when no prediction mask found."""
        with pytest.raises(DeepISLESError, match="No prediction mask found"):
            _find_prediction_mask(tmp_path)


class TestRunDeepISLESDirect:
    """Tests for run_deepisles_direct function.

    Note: These tests don't actually run DeepISLES (which requires the
    DeepISLES Docker image). They test the wrapper logic only.
    """

    def test_missing_input_raises(self, tmp_path: Path) -> None:
        """Raises MissingInputError for missing input files."""
        from stroke_deepisles_demo.inference.direct import run_deepisles_direct

        dwi = tmp_path / "dwi.nii.gz"
        adc = tmp_path / "adc.nii.gz"
        output = tmp_path / "output"

        with pytest.raises(MissingInputError):
            run_deepisles_direct(dwi, adc, output)

    def test_deepisles_not_available_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises DeepISLESError when DeepISLES not available."""
        from stroke_deepisles_demo.inference.direct import run_deepisles_direct

        # Create input files
        dwi = tmp_path / "dwi.nii.gz"
        adc = tmp_path / "adc.nii.gz"
        output = tmp_path / "output"
        dwi.touch()
        adc.touch()

        # Ensure DeepISLES is not importable
        monkeypatch.delenv("DEEPISLES_DIRECT_INVOCATION", raising=False)

        with pytest.raises(DeepISLESError, match="DeepISLES modules not found"):
            run_deepisles_direct(dwi, adc, output)
