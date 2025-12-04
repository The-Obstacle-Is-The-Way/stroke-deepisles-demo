"""Tests for data staging module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from stroke_deepisles_demo.core.exceptions import MissingInputError
from stroke_deepisles_demo.core.types import CaseFiles
from stroke_deepisles_demo.data.staging import (
    create_staging_directory,
    stage_case_for_deepisles,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestCreateStagingDirectory:
    """Tests for create_staging_directory."""

    def test_creates_directory(self, temp_dir: Path) -> None:
        """Staging directory is created and exists."""
        staging = create_staging_directory(base_dir=temp_dir)
        assert staging.exists()
        assert staging.is_dir()

    def test_uses_system_temp_when_no_base(self) -> None:
        """Uses system temp directory when base_dir is None."""
        staging = create_staging_directory(base_dir=None)
        assert staging.exists()
        # Cleanup
        staging.rmdir()


class TestStageCaseForDeepIsles:
    """Tests for stage_case_for_deepisles."""

    def test_stages_required_files(self, synthetic_case_files: CaseFiles, temp_dir: Path) -> None:
        """DWI and ADC are staged with correct names."""
        output_dir = temp_dir / "staged"
        staged = stage_case_for_deepisles(synthetic_case_files, output_dir)

        assert staged.dwi_path.name == "dwi.nii.gz"
        assert staged.adc_path.name == "adc.nii.gz"
        assert staged.dwi_path.exists()
        assert staged.adc_path.exists()

    def test_staged_files_are_readable(
        self, synthetic_case_files: CaseFiles, temp_dir: Path
    ) -> None:
        """Staged files can be read as valid NIfTI."""
        import nibabel as nib

        output_dir = temp_dir / "staged"
        staged = stage_case_for_deepisles(synthetic_case_files, output_dir)

        dwi = nib.load(staged.dwi_path)  # type: ignore
        assert dwi.shape == (64, 64, 30)  # type: ignore

    def test_raises_when_dwi_missing(self, temp_dir: Path) -> None:
        """Raises MissingInputError when DWI is missing."""
        case_files = CaseFiles(
            dwi=temp_dir / "nonexistent.nii.gz",
            adc=temp_dir / "adc.nii.gz",
        )

        with pytest.raises(MissingInputError, match="Source file does not exist"):
            stage_case_for_deepisles(case_files, temp_dir)

    def test_flair_is_optional(self, synthetic_case_files: CaseFiles, temp_dir: Path) -> None:
        """Staging succeeds when FLAIR is None."""
        output_dir = temp_dir / "staged"
        staged = stage_case_for_deepisles(synthetic_case_files, output_dir)

        assert staged.flair_path is None
