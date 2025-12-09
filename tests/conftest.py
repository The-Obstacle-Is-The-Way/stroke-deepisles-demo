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
    from collections.abc import Generator


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
def synthetic_probability_mask(temp_dir: Path) -> Path:
    """
    Create a synthetic probability mask (float values 0.0-1.0).

    This simulates model output that may contain probability values
    rather than binary 0/1 masks. Used to test visualization handling
    of probability-valued segmentation masks.

    The mask has values ONLY at slice 5 to ensure get_slice_at_max_lesion selects it:
    - Outer region with low probability (0.3) - below 0.5 threshold
    - Inner region with high probability (0.8) - above 0.5 threshold

    See: docs/specs/23-slice-comparison-overlay-bug.md
    """
    mask_data = np.zeros((10, 10, 10), dtype=np.float32)

    # Only populate slice 5 to ensure it's selected as max lesion slice
    # Outer region: low confidence (below 0.5 threshold)
    mask_data[2:8, 2:8, 5] = 0.3
    # Inner region: high confidence (above 0.5 threshold) - this should be visible
    mask_data[3:7, 3:7, 5] = 0.8

    img = nib.Nifti1Image(mask_data, affine=np.eye(4))  # type: ignore
    path = temp_dir / "probability_mask.nii.gz"
    nib.save(img, path)  # type: ignore
    return path


@pytest.fixture
def synthetic_binary_mask(temp_dir: Path) -> Path:
    """Create a synthetic binary mask (0 or 1 values only)."""
    mask_data = np.zeros((10, 10, 10), dtype=np.uint8)
    mask_data[3:7, 3:7, 4:6] = 1  # Binary lesion region

    img = nib.Nifti1Image(mask_data, affine=np.eye(4))  # type: ignore
    path = temp_dir / "binary_mask.nii.gz"
    nib.save(img, path)  # type: ignore
    return path


@pytest.fixture
def synthetic_isles_dir(temp_dir: Path) -> Path:
    """
    Create synthetic ISLES24-like directory structure.

    Structure:
        temp_dir/
        ├── Images-DWI/
        │   ├── sub-stroke0001_ses-02_dwi.nii.gz
        │   └── sub-stroke0002_ses-02_dwi.nii.gz
        ├── Images-ADC/
        │   ├── sub-stroke0001_ses-02_adc.nii.gz
        │   └── sub-stroke0002_ses-02_adc.nii.gz
        └── Masks/
            ├── sub-stroke0001_ses-02_lesion-msk.nii.gz
            └── sub-stroke0002_ses-02_lesion-msk.nii.gz
    """
    dwi_dir = temp_dir / "Images-DWI"
    adc_dir = temp_dir / "Images-ADC"
    mask_dir = temp_dir / "Masks"

    dwi_dir.mkdir()
    adc_dir.mkdir()
    mask_dir.mkdir()

    for subject_num in [1, 2]:
        subject_id = f"sub-stroke{subject_num:04d}"

        # Create DWI
        dwi_data = np.random.rand(10, 10, 5).astype(np.float32)
        dwi_img = nib.Nifti1Image(dwi_data, affine=np.eye(4))  # type: ignore
        nib.save(dwi_img, dwi_dir / f"{subject_id}_ses-02_dwi.nii.gz")  # type: ignore

        # Create ADC
        adc_data = np.random.rand(10, 10, 5).astype(np.float32) * 2000
        adc_img = nib.Nifti1Image(adc_data, affine=np.eye(4))  # type: ignore
        nib.save(adc_img, adc_dir / f"{subject_id}_ses-02_adc.nii.gz")  # type: ignore

        # Create Mask
        mask_data = (np.random.rand(10, 10, 5) > 0.9).astype(np.uint8)
        mask_img = nib.Nifti1Image(mask_data, affine=np.eye(4))  # type: ignore
        nib.save(mask_img, mask_dir / f"{subject_id}_ses-02_lesion-msk.nii.gz")  # type: ignore

    return temp_dir
