"""Shared test fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import nibabel as nib
import numpy as np
import pytest

from stroke_deepisles_demo.core.types import CaseFiles

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def synthetic_nifti_3d(temp_dir: Path) -> Path:
    """Create a minimal synthetic 3D NIfTI file."""
    data = np.random.rand(10, 10, 10).astype(np.float32)
    img = nib.Nifti1Image(data, affine=np.eye(4))  # type: ignore
    path = temp_dir / "synthetic.nii.gz"
    nib.save(img, path)  # type: ignore
    return path


@pytest.fixture
def synthetic_case_files(temp_dir: Path) -> CaseFiles:
    """Create a complete set of synthetic case files."""
    # Create DWI
    dwi_data = np.random.rand(64, 64, 30).astype(np.float32)
    dwi_img = nib.Nifti1Image(dwi_data, affine=np.eye(4))  # type: ignore
    dwi_path = temp_dir / "dwi.nii.gz"
    nib.save(dwi_img, dwi_path)  # type: ignore

    # Create ADC
    adc_data = np.random.rand(64, 64, 30).astype(np.float32) * 2000
    adc_img = nib.Nifti1Image(adc_data, affine=np.eye(4))  # type: ignore
    adc_path = temp_dir / "adc.nii.gz"
    nib.save(adc_img, adc_path)  # type: ignore

    # Create mask
    mask_data = (np.random.rand(64, 64, 30) > 0.9).astype(np.uint8)
    mask_img = nib.Nifti1Image(mask_data, affine=np.eye(4))  # type: ignore
    mask_path = temp_dir / "mask.nii.gz"
    nib.save(mask_img, mask_path)  # type: ignore

    return CaseFiles(
        dwi=dwi_path,
        adc=adc_path,
        ground_truth=mask_path,
    )


@pytest.fixture
def mock_hf_dataset(synthetic_case_files: CaseFiles) -> object:
    """Create a mock HF Dataset-like object."""

    # Simple list-based mock that mimics dataset behavior
    class MockDataset:
        def __init__(self) -> None:
            self.data = [
                {
                    "participant_id": "sub-001",
                    "dwi": str(synthetic_case_files["dwi"]),
                    "adc": str(synthetic_case_files["adc"]),
                    "flair": None,
                    "mask": str(synthetic_case_files.get("ground_truth")),
                }
            ]
            self.features = {"dwi": None, "adc": None, "flair": None, "mask": None}

        def __len__(self) -> int:
            return len(self.data)

        def __getitem__(self, idx: int) -> dict[str, str | None]:
            return self.data[idx]

        def __iter__(self) -> Iterator[dict[str, str | None]]:
            return iter(self.data)

    return MockDataset()
