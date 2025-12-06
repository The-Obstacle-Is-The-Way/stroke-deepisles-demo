"""Neuroimaging visualization for Gradio.

This module provides visualization components for neuroimaging data:
- NiiVue WebGL-based 3D viewer
- Matplotlib-based 2D slice comparisons

See:
    - https://github.com/niivue/niivue (NiiVue v0.65.0)
    - docs/specs/07-hf-spaces-deployment.md
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

from stroke_deepisles_demo.metrics import load_nifti_as_array

if TYPE_CHECKING:
    from pathlib import Path

    from matplotlib.figure import Figure

# NiiVue version - updated to latest stable (Dec 2025)
NIIVUE_VERSION = "0.65.0"
NIIVUE_CDN_URL = f"https://unpkg.com/@niivue/niivue@{NIIVUE_VERSION}/dist/index.js"


def nifti_to_data_url(nifti_path: Path) -> str:
    """
    Convert NIfTI file to base64 data URL for NiiVue.

    Args:
        nifti_path: Path to NIfTI file

    Returns:
        Data URL string
    """
    # We load the raw bytes directly to avoid re-serialization overhead if possible
    # But nibabel might be safer to ensure valid nifti if we were manipulating
    # Here we just want the file content.
    with nifti_path.open("rb") as f:
        nifti_bytes = f.read()

    nifti_b64 = base64.b64encode(nifti_bytes).decode("utf-8")
    return f"data:application/octet-stream;base64,{nifti_b64}"


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

    # Create figure
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor("black")

    # Axial (XY plane, Z fixed) - often needs rotation 90 deg
    # NIfTI data[x, y, z]. To display standard axial:
    # usually imshow(data[:, :, z].T, origin='lower')
    ax_slice = np.rot90(data[:, :, mid_z])
    axes[0].imshow(ax_slice, cmap="gray")
    axes[0].set_title(f"Axial (z={mid_z})", color="white")
    if mask_data is not None:
        m_slice = np.rot90(mask_data[:, :, mid_z])
        axes[0].imshow(
            np.ma.masked_where(m_slice == 0, m_slice),  # type: ignore[no-untyped-call]
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
        axes[1].imshow(
            np.ma.masked_where(m_slice == 0, m_slice),  # type: ignore[no-untyped-call]
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
        axes[2].imshow(
            np.ma.masked_where(m_slice == 0, m_slice),  # type: ignore[no-untyped-call]
            cmap="Reds",
            alpha=mask_alpha,
            vmin=0,
            vmax=1,
        )

    for ax in axes:
        ax.axis("off")

    plt.tight_layout()
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
    fig, axes = plt.subplots(1, num_plots, figsize=(5 * num_plots, 5))
    fig.patch.set_facecolor("black")
    if num_plots == 2:
        axes = np.array(axes)  # handle single case if needed, but subplots(1,2) returns array

    # 1. DWI
    axes[0].imshow(d_slice, cmap="gray")
    axes[0].set_title("DWI Input", color="white")

    # 2. Prediction
    axes[1].imshow(d_slice, cmap="gray")
    axes[1].imshow(
        np.ma.masked_where(p_slice == 0, p_slice),  # type: ignore[no-untyped-call]
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

    plt.tight_layout()
    return fig


def create_niivue_html(
    volume_url: str,
    mask_url: str | None = None,
    *,
    height: int = 400,
) -> str:
    """
    Create HTML/JS for NiiVue viewer.

    This function generates an HTML snippet with embedded JavaScript for
    NiiVue WebGL-based neuroimaging visualization. Each invocation creates
    a unique canvas ID to avoid conflicts when multiple viewers are rendered.

    Args:
        volume_url: Data URL or URL to volume NIfTI file
        mask_url: Optional data URL or URL to mask NIfTI file
        height: Viewer height in pixels

    Returns:
        HTML string with embedded NiiVue viewer

    Note:
        The JavaScript uses dynamic import() which works in modern browsers
        and Gradio's HTML component. Each viewer gets a unique ID to support
        multiple simultaneous viewers.
    """
    # Generate unique ID for this viewer instance
    viewer_id = uuid.uuid4().hex[:8]
    canvas_id = f"niivue-canvas-{viewer_id}"
    container_id = f"niivue-container-{viewer_id}"

    # Safely serialize URLs for JavaScript (prevents XSS)
    volume_url_js = json.dumps(volume_url)

    # Build mask volume configuration if provided
    mask_js = ""
    if mask_url:
        mask_url_js = json.dumps(mask_url)
        mask_js = f"""
                volumes.push({{
                    url: {mask_url_js},
                    colorMap: 'red',
                    opacity: 0.5
                }});"""

    # JavaScript that initializes NiiVue
    # Using an IIFE pattern that works better in Gradio's HTML component
    return f"""
    <div id="{container_id}" style="width:100%; height:{height}px; background:#000; border-radius:8px; position:relative;">
        <canvas id="{canvas_id}" style="width:100%; height:100%;"></canvas>
    </div>
    <script type="module">
        // NiiVue initialization for viewer {viewer_id}
        (async function() {{
            try {{
                // Check if browser supports WebGL2
                const testCanvas = document.createElement('canvas');
                const gl = testCanvas.getContext('webgl2');
                if (!gl) {{
                    document.getElementById('{container_id}').innerHTML =
                        '<div style="color:#fff;padding:20px;text-align:center;">' +
                        'WebGL2 not supported. Please use a modern browser.</div>';
                    return;
                }}

                // Dynamically import NiiVue
                const niivueModule = await import('{NIIVUE_CDN_URL}');
                const Niivue = niivueModule.Niivue;

                // Initialize NiiVue with options
                const nv = new Niivue({{
                    logging: false,
                    show3Dcrosshair: true,
                    textHeight: 0.04,
                    backColor: [0, 0, 0, 1],
                    crosshairColor: [0.2, 0.8, 0.2, 1]
                }});

                // Attach to canvas
                await nv.attachToCanvas(document.getElementById('{canvas_id}'));

                // Prepare volumes
                const volumes = [{{
                    url: {volume_url_js},
                    name: 'input.nii.gz'
                }}];{mask_js}

                // Load volumes
                await nv.loadVolumes(volumes);

                // Configure view: multiplanar + 3D
                nv.setSliceType(nv.sliceTypeMultiplanar);
                if (typeof nv.setMultiplanarLayout === 'function') {{
                    nv.setMultiplanarLayout(2);
                }}
                nv.opts.show3Dcrosshair = true;
                nv.setRenderAzimuthElevation(120, 10);
                nv.drawScene();

                console.log('NiiVue viewer {viewer_id} initialized successfully');
            }} catch (error) {{
                console.error('NiiVue initialization error:', error);
                document.getElementById('{container_id}').innerHTML =
                    '<div style="color:#fff;padding:20px;text-align:center;">' +
                    'Error loading viewer: ' + error.message + '</div>';
            }}
        }})();
    </script>
    """
