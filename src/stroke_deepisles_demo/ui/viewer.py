"""Neuroimaging visualization for Gradio.

This module provides visualization components for neuroimaging data:
- NiiVue WebGL-based 3D viewer
- Matplotlib-based 2D slice comparisons

See:
    - https://github.com/niivue/niivue (NiiVue v0.65.0)
    - docs/specs/07-hf-spaces-deployment.md
    - docs/specs/19-perf-base64-to-file-urls.md (Issue #19 optimization)
"""

from __future__ import annotations

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
    Create HTML for NiiVue viewer (static content only).

    This function generates an HTML snippet with data attributes containing
    volume URLs. The actual NiiVue initialization is handled by js_on_load
    in the gr.HTML component (see NIIVUE_ON_LOAD_JS).

    IMPORTANT: Gradio's gr.HTML strips <script> tags for security.
    JavaScript must be passed via the js_on_load parameter instead.

    Args:
        volume_url: Gradio file URL (e.g., /gradio_api/file=/path/to/file.nii.gz)
        mask_url: Optional Gradio file URL to mask NIfTI file
        height: Viewer height in pixels

    Returns:
        HTML string with data attributes for NiiVue viewer

    Note:
        The volume URLs are stored in data-* attributes and read by
        the js_on_load JavaScript code. This pattern works because
        js_on_load has access to the 'element' variable.
    """
    # Generate unique ID for this viewer instance
    viewer_id = uuid.uuid4().hex[:8]

    # Safely encode URLs for HTML data attributes
    # Using json.dumps ensures proper escaping
    volume_attr = f"data-volume-url={json.dumps(volume_url)}"
    mask_attr = f"data-mask-url={json.dumps(mask_url)}" if mask_url else 'data-mask-url=""'

    return f"""<div
    id="niivue-container-{viewer_id}"
    class="niivue-viewer"
    {volume_attr}
    {mask_attr}
    style="width:100%; height:{height}px; background:#000; border-radius:8px; position:relative;"
>
    <canvas style="width:100%; height:100%;"></canvas>
    <div class="niivue-status" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#666;">
        Loading viewer...
    </div>
</div>"""


# JavaScript code for js_on_load parameter
# This runs when the gr.HTML component FIRST loads (mounts)
# Variables available: element, props, trigger
NIIVUE_ON_LOAD_JS = f"""
(async () => {{
    const container = element.querySelector('.niivue-viewer') || element;
    const canvas = element.querySelector('canvas');
    const status = element.querySelector('.niivue-status');

    // Get URLs from data attributes
    const volumeUrl = container.dataset.volumeUrl;
    const maskUrl = container.dataset.maskUrl;

    // Skip if no volume URL (initial empty state)
    if (!volumeUrl) {{
        if (status) status.innerText = 'Waiting for segmentation...';
        return;
    }}

    try {{
        if (status) status.innerText = 'Checking WebGL2...';

        // Check WebGL2 support
        const gl = canvas.getContext('webgl2');
        if (!gl) {{
            container.innerHTML = '<div style="color:#fff;padding:20px;text-align:center;">WebGL2 not supported. Please use a modern browser.</div>';
            return;
        }}

        if (status) status.innerText = 'Loading NiiVue...';

        // Dynamically import NiiVue from CDN
        const {{ Niivue }} = await import('{NIIVUE_CDN_URL}');

        // Initialize NiiVue
        const nv = new Niivue({{
            logging: false,
            show3Dcrosshair: true,
            textHeight: 0.04,
            backColor: [0, 0, 0, 1],
            crosshairColor: [0.2, 0.8, 0.2, 1]
        }});

        // Attach to canvas
        await nv.attachToCanvas(canvas);

        // Hide status message
        if (status) status.style.display = 'none';

        // Prepare volumes
        const volumes = [{{ url: volumeUrl, name: 'input.nii.gz' }}];

        if (maskUrl) {{
            volumes.push({{
                url: maskUrl,
                colorMap: 'red',
                opacity: 0.5
            }});
        }}

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

        console.log('NiiVue viewer initialized successfully');

    }} catch (error) {{
        console.error('NiiVue initialization error:', error);
        // Use textContent instead of innerHTML to prevent XSS
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'color:#f66;padding:20px;text-align:center;';
        errorDiv.textContent = 'Error loading viewer: ' + error.message;
        container.innerHTML = '';
        container.appendChild(errorDiv);
    }}
}})();
"""

# JavaScript code for event handlers (e.g. .then(js=...))
# This runs after Python updates the HTML value.
# ⚠️ CRITICAL: 'element' is NOT available here! Must use document.querySelector
NIIVUE_UPDATE_JS = f"""
(async () => {{
    // We must find the container globally since 'element' is not available in event handlers
    const container = document.querySelector('.niivue-viewer');

    if (!container) {{
        console.error('NiiVue container not found');
        return;
    }}

    const canvas = container.querySelector('canvas');
    const status = container.querySelector('.niivue-status');

    // Get URLs from data attributes
    const volumeUrl = container.dataset.volumeUrl;
    const maskUrl = container.dataset.maskUrl;

    // Skip if no volume URL
    if (!volumeUrl) {{
        return;
    }}

    try {{
        if (status) status.innerText = 'Reloading NiiVue...';

        // Check WebGL2 support
        const gl = canvas.getContext('webgl2');
        if (!gl) {{
            container.innerHTML = '<div style="color:#fff;padding:20px;text-align:center;">WebGL2 not supported. Please use a modern browser.</div>';
            return;
        }}

        // Dynamically import NiiVue from CDN
        const {{ Niivue }} = await import('{NIIVUE_CDN_URL}');

        // Initialize NiiVue
        const nv = new Niivue({{
            logging: false,
            show3Dcrosshair: true,
            textHeight: 0.04,
            backColor: [0, 0, 0, 1],
            crosshairColor: [0.2, 0.8, 0.2, 1]
        }});

        // Attach to canvas
        await nv.attachToCanvas(canvas);

        // Hide status message
        if (status) status.style.display = 'none';

        // Prepare volumes
        const volumes = [{{ url: volumeUrl, name: 'input.nii.gz' }}];

        if (maskUrl) {{
            volumes.push({{
                url: maskUrl,
                colorMap: 'red',
                opacity: 0.5
            }});
        }}

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

        console.log('NiiVue viewer re-initialized successfully via event handler');

    }} catch (error) {{
        console.error('NiiVue re-initialization error:', error);
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'color:#f66;padding:20px;text-align:center;';
        errorDiv.textContent = 'Error reloading viewer: ' + error.message;
        if (container) {{
            container.innerHTML = '';
            container.appendChild(errorDiv);
        }}
    }}
}})();
"""
