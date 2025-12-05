"""Tests for metrics module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import nibabel as nib
import numpy as np
import pytest

from stroke_deepisles_demo.metrics import (
    compute_dice,
    compute_volume_ml,
    load_nifti_as_array,
)

if TYPE_CHECKING:
    from pathlib import Path


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
        img = nib.Nifti1Image(mask, np.eye(4))  # type: ignore[attr-defined, no-untyped-call]

        pred_path = temp_dir / "pred.nii.gz"
        gt_path = temp_dir / "gt.nii.gz"
        nib.save(img, pred_path)  # type: ignore[attr-defined]
        nib.save(img, gt_path)  # type: ignore[attr-defined]

        dice = compute_dice(pred_path, gt_path)

        assert dice == 1.0

    def test_shape_mismatch_raises(self) -> None:
        """Raises ValueError if shapes don't match."""
        pred = np.zeros((10, 10, 10))
        gt = np.zeros((10, 10, 5))

        with pytest.raises(ValueError, match="Shape mismatch"):
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
        img = nib.Nifti1Image(mask, affine)  # type: ignore[attr-defined, no-untyped-call]

        path = temp_dir / "mask.nii.gz"
        nib.save(img, path)  # type: ignore[attr-defined]

        # 1000 voxels * 8mm^3 = 8000mm^3 = 8mL
        volume = compute_volume_ml(path)

        assert volume == pytest.approx(8.0, rel=0.01)


class TestLoadNiftiAsArray:
    """Tests for load_nifti_as_array."""

    def test_returns_array_and_voxel_sizes(self, temp_dir: Path) -> None:
        """Returns data array and voxel dimensions."""
        data = np.random.rand(10, 10, 10).astype(np.float32)
        affine = np.diag([1.5, 1.5, 2.0, 1.0])
        img = nib.Nifti1Image(data, affine)  # type: ignore[attr-defined, no-untyped-call]

        path = temp_dir / "test.nii.gz"
        nib.save(img, path)  # type: ignore[attr-defined]

        arr, voxels = load_nifti_as_array(path)

        assert arr.shape == (10, 10, 10)
        assert voxels == pytest.approx((1.5, 1.5, 2.0), rel=0.01)
