"""Metrics for evaluating segmentation quality."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

import nibabel as nib
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def load_nifti_as_array(path: Path) -> tuple[NDArray[np.floating[Any]], tuple[float, float, float]]:
    """
    Load NIfTI file and return data array with voxel dimensions.

    Args:
        path: Path to NIfTI file

    Returns:
        Tuple of (data_array, voxel_sizes_mm)
    """
    img = nib.load(path)  # type: ignore[attr-defined]
    # Use float32 for memory efficiency (sufficient for medical images)
    data = img.get_fdata(dtype=np.float32)  # type: ignore[attr-defined]
    zooms = img.header.get_zooms()  # type: ignore[attr-defined]
    # zooms can be 3D or 4D, we want spatial dims. DeepISLES output is 3D.
    # Extract exactly 3 spatial dimensions.
    spatial_zooms = zooms[:3]
    voxel_sizes: tuple[float, float, float] = (
        float(spatial_zooms[0]),
        float(spatial_zooms[1]),
        float(spatial_zooms[2]),
    )
    return data, voxel_sizes


def compute_dice(
    prediction: Path | NDArray[np.floating[Any]],
    ground_truth: Path | NDArray[np.floating[Any]],
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
    if isinstance(prediction, Path):
        p_data, _ = load_nifti_as_array(prediction)
    else:
        p_data = prediction

    if isinstance(ground_truth, Path):
        g_data, _ = load_nifti_as_array(ground_truth)
    else:
        g_data = ground_truth

    if p_data.shape != g_data.shape:
        raise ValueError(
            f"Shape mismatch: prediction {p_data.shape} vs ground truth {g_data.shape}"
        )

    # Binarize
    p_bin = (p_data > threshold).astype(bool)
    g_bin = (g_data > threshold).astype(bool)

    intersection = np.sum(p_bin & g_bin)
    total = np.sum(p_bin) + np.sum(g_bin)

    if total == 0:
        return 1.0  # Both empty

    return float(2.0 * intersection / total)


def compute_volume_ml(
    mask: Path | NDArray[np.floating[Any]],
    voxel_size_mm: tuple[float, float, float] | None = None,
    *,
    threshold: float = 0.5,
) -> float:
    """
    Compute lesion volume in milliliters.

    Args:
        mask: Path to NIfTI file or numpy array
        voxel_size_mm: Voxel dimensions in mm (read from NIfTI if None)
        threshold: Threshold for binarization (default 0.5 for consistency with compute_dice)

    Returns:
        Volume in milliliters (mL)

    Note:
        Uses the same default threshold (0.5) as compute_dice for consistency.
        This ensures the volume measurement matches the clinical segmentation decision boundary.
    """
    if isinstance(mask, Path):
        data, loaded_zooms = load_nifti_as_array(mask)
        voxel_dims = voxel_size_mm if voxel_size_mm is not None else loaded_zooms
    else:
        data = mask
        # Default to 1mm isotropic if not provided for array
        voxel_dims = voxel_size_mm if voxel_size_mm is not None else (1.0, 1.0, 1.0)

    # Binarize at threshold for consistent measurement with compute_dice
    volume_voxels = np.sum(data > threshold)
    voxel_vol_mm3 = math.prod(voxel_dims)

    return float(volume_voxels * voxel_vol_mm3 / 1000.0)  # mm3 -> mL
