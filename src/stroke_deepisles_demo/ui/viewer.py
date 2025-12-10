"""Neuroimaging visualization for Gradio.

This module provides visualization components for neuroimaging data:
- Matplotlib-based 2D slice comparisons
- NIfTI URL helper for Custom Component

See:
    - docs/specs/07-hf-spaces-deployment.md
    - docs/specs/19-perf-base64-to-file-urls.md (Issue #19 optimization)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.metrics import load_nifti_as_array

logger = get_logger(__name__)


def nifti_to_gradio_url(nifti_path: Path) -> str:
    """
    Get Gradio file URL for a NIfTI file.

    Uses Gradio's built-in file serving instead of base64 encoding.
    This reduces payload size by ~33% and improves browser performance
    by avoiding large base64 strings in the DOM.

    Args:
        nifti_path: Path to NIfTI file. Must be in an allowed path:
            - tempfile.gettempdir() (default for pipeline results)
            - Current working directory
            - Paths specified in allowed_paths during launch()

    Returns:
        Gradio file URL (e.g., /gradio_api/file=/tmp/.../dwi.nii.gz)

    Note:
        This replaces the deprecated nifti_to_data_url() function.
        See Issue #19 for performance analysis and benchmarks.

    References:
        - https://www.gradio.app/guides/file-access
        - https://niivue.com/docs/loading/
    """
    # Ensure we use absolute path for Gradio's file serving
    abs_path = nifti_path.resolve()

    # Gradio file URL format (standard since Gradio 4.x)
    # Files in tempfile.gettempdir() are allowed by default
    return f"/gradio_api/file={abs_path}"


def get_slice_at_max_lesion(
    mask_path: Path,
    orientation: str = "axial",
) -> int:
    """
    Find slice index with maximum lesion area.

    Useful for displaying the most informative slice.

    Args:
        mask_path: Path to lesion mask NIfTI
        orientation: Slice orientation ("axial", "coronal", "sagittal")

    Returns:
        Slice index with maximum lesion area
    """
    data, _ = load_nifti_as_array(mask_path)

    # Determine axes to sum over
    # Default NIfTI (RAS+): x=sagittal, y=coronal, z=axial
    # array indices: [x, y, z]
    if orientation == "sagittal":
        # Sum over y and z (axes 1, 2) -> result shape [x]
        lesion_counts = np.sum(data > 0, axis=(1, 2))
    elif orientation == "coronal":
        # Sum over x and z (axes 0, 2) -> result shape [y]
        lesion_counts = np.sum(data > 0, axis=(0, 2))
    else:  # axial
        # Sum over x and y (axes 0, 1) -> result shape [z]
        lesion_counts = np.sum(data > 0, axis=(0, 1))

    max_slice = int(np.argmax(lesion_counts))

    # If mask is empty, return middle slice
    if np.max(lesion_counts) == 0:
        if orientation == "sagittal":
            return int(data.shape[0] // 2)
        elif orientation == "coronal":
            return int(data.shape[1] // 2)
        else:
            return int(data.shape[2] // 2)

    return max_slice


def render_3panel_view(
    nifti_path: Path,
    mask_path: Path | None = None,
    *,
    mask_alpha: float = 0.5,
) -> Figure:
    """
    Render axial/coronal/sagittal slices with optional mask overlay.

    Args:
        nifti_path: Path to base NIfTI volume
        mask_path: Optional path to mask for overlay
        mask_alpha: Transparency of mask overlay

    Returns:
        Matplotlib figure with 3-panel view
    """
    data, _ = load_nifti_as_array(nifti_path)
    mask_data = None
    if mask_path:
        mask_data, _ = load_nifti_as_array(mask_path)

    # Get slices (middle by default, or max lesion if mask exists)
    mid_x, mid_y, mid_z = data.shape[0] // 2, data.shape[1] // 2, data.shape[2] // 2

    if mask_data is not None and np.any(mask_data > 0):
        # Try to find a slice that intersects the lesion best
        # Simplified: use center of mass of lesion
        coords = np.argwhere(mask_data > 0)
        center = coords.mean(axis=0).astype(int)
        mid_x, mid_y, mid_z = center[0], center[1], center[2]

    # Create figure using OO API for thread safety
    fig = Figure(figsize=(15, 5))
    fig.patch.set_facecolor("black")
    axes = fig.subplots(1, 3)

    # Axial (XY plane, Z fixed) - often needs rotation 90 deg
    # NIfTI data[x, y, z]. To display standard axial:
    # usually imshow(data[:, :, z].T, origin='lower')
    ax_slice = np.rot90(data[:, :, mid_z])
    axes[0].imshow(ax_slice, cmap="gray")
    axes[0].set_title(f"Axial (z={mid_z})", color="white")
    if mask_data is not None:
        m_slice = np.rot90(mask_data[:, :, mid_z])
        # Binarize at 0.5 threshold for visible overlay (consistent with compute_dice)
        m_slice_binary = (m_slice > 0.5).astype(float)
        axes[0].imshow(
            np.ma.masked_where(m_slice_binary == 0, m_slice_binary),  # type: ignore[no-untyped-call]
            cmap="Reds",
            alpha=mask_alpha,
            vmin=0,
            vmax=1,
        )

    # Coronal (XZ plane, Y fixed)
    cor_slice = np.rot90(data[:, mid_y, :])
    axes[1].imshow(cor_slice, cmap="gray")
    axes[1].set_title(f"Coronal (y={mid_y})", color="white")
    if mask_data is not None:
        m_slice = np.rot90(mask_data[:, mid_y, :])
        # Binarize at 0.5 threshold for visible overlay (consistent with compute_dice)
        m_slice_binary = (m_slice > 0.5).astype(float)
        axes[1].imshow(
            np.ma.masked_where(m_slice_binary == 0, m_slice_binary),  # type: ignore[no-untyped-call]
            cmap="Reds",
            alpha=mask_alpha,
            vmin=0,
            vmax=1,
        )

    # Sagittal (YZ plane, X fixed)
    sag_slice = np.rot90(data[mid_x, :, :])
    axes[2].imshow(sag_slice, cmap="gray")
    axes[2].set_title(f"Sagittal (x={mid_x})", color="white")
    if mask_data is not None:
        m_slice = np.rot90(mask_data[mid_x, :, :])
        # Binarize at 0.5 threshold for visible overlay (consistent with compute_dice)
        m_slice_binary = (m_slice > 0.5).astype(float)
        axes[2].imshow(
            np.ma.masked_where(m_slice_binary == 0, m_slice_binary),  # type: ignore[no-untyped-call]
            cmap="Reds",
            alpha=mask_alpha,
            vmin=0,
            vmax=1,
        )

    for ax in axes:
        ax.axis("off")

    fig.tight_layout()
    return fig


def render_slice_comparison(
    dwi_path: Path,
    prediction_path: Path,
    ground_truth_path: Path | None = None,
    *,
    slice_idx: int | None = None,
    orientation: str = "axial",
) -> Figure:
    """
    Render side-by-side comparison of DWI, prediction, and ground truth.

    Args:
        dwi_path: Path to DWI NIfTI
        prediction_path: Path to predicted mask NIfTI
        ground_truth_path: Optional path to ground truth mask
        slice_idx: Slice index (default: max lesion or middle)
        orientation: One of "axial", "coronal", "sagittal"

    Returns:
        Matplotlib figure with comparison view
    """
    dwi_data, _ = load_nifti_as_array(dwi_path)
    pred_data, _ = load_nifti_as_array(prediction_path)
    gt_data = None
    if ground_truth_path:
        gt_data, _ = load_nifti_as_array(ground_truth_path)

    # Determine slice index
    if slice_idx is None:
        # Use prediction to find best slice
        slice_idx = get_slice_at_max_lesion(prediction_path, orientation)

    # Extract slices based on orientation
    # Assuming data[x, y, z]
    if orientation == "sagittal":
        # X fixed
        d_slice = np.rot90(dwi_data[slice_idx, :, :])
        p_slice = np.rot90(pred_data[slice_idx, :, :])
        g_slice = np.rot90(gt_data[slice_idx, :, :]) if gt_data is not None else None
    elif orientation == "coronal":
        # Y fixed
        d_slice = np.rot90(dwi_data[:, slice_idx, :])
        p_slice = np.rot90(pred_data[:, slice_idx, :])
        g_slice = np.rot90(gt_data[:, slice_idx, :]) if gt_data is not None else None
    else:
        # Z fixed (axial)
        d_slice = np.rot90(dwi_data[:, :, slice_idx])
        p_slice = np.rot90(pred_data[:, :, slice_idx])
        g_slice = np.rot90(gt_data[:, :, slice_idx]) if gt_data is not None else None

    # Plotting
    num_plots = 3 if gt_data is not None else 2
    # Create figure using OO API for thread safety
    fig = Figure(figsize=(5 * num_plots, 5))
    fig.patch.set_facecolor("black")
    axes = fig.subplots(1, num_plots)

    if num_plots == 2:
        axes = np.array(axes)  # handle single case if needed, but subplots(1,2) returns array

    # 1. DWI
    axes[0].imshow(d_slice, cmap="gray")
    axes[0].set_title("DWI Input", color="white")

    # 2. Prediction
    # Binarize prediction at threshold 0.5 for visible overlay (Issue #23)
    # Model output may contain probability values (0.0-1.0) which render as
    # nearly-white in the "Reds" colormap. Binarizing ensures consistent
    # visualization matching how compute_dice() evaluates predictions.
    p_slice_binary = (p_slice > 0.5).astype(float)
    axes[1].imshow(d_slice, cmap="gray")
    axes[1].imshow(
        np.ma.masked_where(p_slice_binary == 0, p_slice_binary),  # type: ignore[no-untyped-call]
        cmap="Reds",
        alpha=0.5,
        vmin=0,
        vmax=1,
    )
    axes[1].set_title("Prediction", color="white")

    # 3. GT (if available)
    if gt_data is not None:
        axes[2].imshow(d_slice, cmap="gray")
        axes[2].imshow(
            np.ma.masked_where(g_slice == 0, g_slice),  # type: ignore[no-untyped-call]
            cmap="Greens",
            alpha=0.5,
            vmin=0,
            vmax=1,
        )
        axes[2].set_title("Ground Truth", color="white")

    for ax in axes:
        ax.axis("off")

    fig.tight_layout()
    return fig
