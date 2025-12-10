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
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.metrics import load_nifti_as_array

logger = get_logger(__name__)

# NiiVue version - updated to latest stable (Dec 2025)
# Switched to local vendoring to avoid CSP issues on HuggingFace Spaces (Issue #24)
# The file is located in src/stroke_deepisles_demo/ui/assets/niivue.js
NIIVUE_VERSION = "0.65.0"
_ASSET_DIR = Path(__file__).parent / "assets"
_NIIVUE_JS_PATH = _ASSET_DIR / "niivue.js"

# Ensure absolute path for Gradio serving
# NOTE: This path must be added to allowed_paths AND set_static_paths in demo.launch()
NIIVUE_JS_URL = f"/gradio_api/file={_NIIVUE_JS_PATH.resolve()}"

# Log the computed paths at module load time for debugging HF Spaces issues
logger.info("NiiVue assets directory: %s", _ASSET_DIR.resolve())
logger.info("NiiVue JS path: %s", _NIIVUE_JS_PATH.resolve())
logger.info("NiiVue JS URL: %s", NIIVUE_JS_URL)
logger.info("NiiVue JS exists: %s", _NIIVUE_JS_PATH.exists())


def get_niivue_head_html() -> str:
    """
    Get HTML content to inject into page <head> for NiiVue loading.

    This returns an inline script that loads NiiVue as a global variable.
    Using the `head` parameter directly (instead of `head_paths` with a file)
    is simpler and avoids file I/O issues on HF Spaces.

    Returns:
        HTML string containing the NiiVue loader script

    Note:
        The niivue.js path must be registered with gr.set_static_paths()
        and included in allowed_paths during launch().
    """
    # Log for debugging path resolution issues on HF Spaces
    logger.info("Generating NiiVue head HTML with URL: %s", NIIVUE_JS_URL)

    return f"""<!-- NiiVue Loader: Exposes window.Niivue for js_on_load handlers -->
<script type="module">
    try {{
        const niivueUrl = '{NIIVUE_JS_URL}';
        console.log('[NiiVue Loader] Attempting to load from:', niivueUrl);
        const {{ Niivue }} = await import(niivueUrl);
        window.Niivue = Niivue;
        console.log('[NiiVue Loader] Successfully loaded, window.Niivue:', typeof window.Niivue);
    }} catch (error) {{
        console.error('[NiiVue Loader] FAILED to load:', error);
        // Surface the error visibly so we can debug on HF Spaces
        window.NIIVUE_LOAD_ERROR = error.message;
    }}
</script>
"""


def get_niivue_loader_path() -> Path:
    """
    DEPRECATED: Use get_niivue_head_html() with the `head` parameter instead.

    Get path to the NiiVue loader HTML file, creating it if needed.
    This file-based approach is kept for backwards compatibility but
    the direct `head` parameter approach is preferred.

    Returns:
        Path to the niivue-loader.html file
    """
    loader_path = _ASSET_DIR / "niivue-loader.html"
    loader_content = get_niivue_head_html()

    try:
        if loader_path.exists():
            existing_content = loader_path.read_text()
            if existing_content == loader_content:
                return loader_path

        loader_path.write_text(loader_content)
        logger.debug("Generated NiiVue loader at %s", loader_path)
    except OSError as e:
        logger.warning("Could not write loader file at %s: %s", loader_path, e)
        if not loader_path.exists():
            raise RuntimeError(
                f"NiiVue loader file not found and cannot be created: {loader_path}"
            ) from e

    return loader_path


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


def create_niivue_html(
    volume_url: str,
    mask_url: str | None = None,
    *,
    height: int = 400,
) -> str:
    """
    Create HTML for NiiVue viewer (static content only).

    This function generates an HTML snippet with data attributes containing
    volume URLs AND the NiiVue library URL. The actual NiiVue initialization
    is handled by js_on_load in the gr.HTML component (see NIIVUE_ON_LOAD_JS).

    IMPORTANT: Gradio's gr.HTML strips <script> tags for security.
    JavaScript must be passed via the js_on_load parameter instead.

    The NiiVue library URL is embedded in data-niivue-url so that js_on_load
    can load the library on-demand. This removes the dependency on the `head=`
    parameter working correctly, which has been problematic on HF Spaces.

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
    # Embed NiiVue library URL so js_on_load can load it directly
    # This removes dependency on head= script working on HF Spaces
    niivue_url_attr = f"data-niivue-url={json.dumps(NIIVUE_JS_URL)}"

    return f"""<div
    id="niivue-container-{viewer_id}"
    class="niivue-viewer"
    {volume_attr}
    {mask_attr}
    {niivue_url_attr}
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
#
# CRITICAL FIX (Issue #24): This code loads NiiVue DIRECTLY via dynamic import()
# from the data-niivue-url attribute. This removes the dependency on the `head=`
# parameter which was blocking Gradio initialization on HF Spaces.
#
# The old approach used window.Niivue from a head script, but ES module failures
# in <head> can prevent Gradio's Svelte app from hydrating, causing "Loading..." forever.
NIIVUE_ON_LOAD_JS = """
(async () => {
    const container = element.querySelector('.niivue-viewer') || element;
    const canvas = element.querySelector('canvas');
    const status = element.querySelector('.niivue-status');

    // Get URLs from data attributes
    const volumeUrl = container.dataset.volumeUrl;
    const maskUrl = container.dataset.maskUrl;
    const niivueUrl = container.dataset.niivueUrl;

    // Skip if no volume URL (initial empty state)
    if (!volumeUrl) {
        if (status) status.innerText = 'Waiting for segmentation...';
        return;
    }

    try {
        if (status) status.innerText = 'Checking WebGL2...';

        // Check WebGL2 support
        const gl = canvas.getContext('webgl2');
        if (!gl) {
            container.innerHTML = '<div style="color:#fff;padding:20px;text-align:center;">WebGL2 not supported. Please use a modern browser.</div>';
            return;
        }

        if (status) status.innerText = 'Loading NiiVue library...';

        // Load NiiVue directly (self-sufficient, no head= dependency)
        // This fixes the HF Spaces "Loading..." forever bug (Issue #24)
        const loadNiivue = async () => {
            // Return cached if already loaded
            if (window.Niivue) {
                console.log('[NiiVue] Using cached window.Niivue');
                return window.Niivue;
            }

            // Load directly from the URL embedded in data attribute
            if (!niivueUrl) {
                throw new Error('No NiiVue URL provided in data-niivue-url attribute');
            }

            console.log('[NiiVue] Loading from:', niivueUrl);
            try {
                const module = await import(niivueUrl);
                window.Niivue = module.Niivue;
                console.log('[NiiVue] Successfully loaded and cached');
                return module.Niivue;
            } catch (e) {
                // Provide detailed error for debugging
                console.error('[NiiVue] Import failed:', e);
                throw new Error('Failed to load NiiVue from ' + niivueUrl + ': ' + e.message);
            }
        };

        const Niivue = await loadNiivue();

        // Initialize NiiVue
        const nv = new Niivue({
            logging: false,
            show3Dcrosshair: true,
            textHeight: 0.04,
            backColor: [0, 0, 0, 1],
            crosshairColor: [0.2, 0.8, 0.2, 1]
        });

        // Attach to canvas
        await nv.attachToCanvas(canvas);

        // Hide status message
        if (status) status.style.display = 'none';

        // Prepare volumes
        const volumes = [{ url: volumeUrl, name: 'input.nii.gz' }];

        if (maskUrl) {
            volumes.push({
                url: maskUrl,
                colorMap: 'red',
                opacity: 0.5
            });
        }

        // Load volumes
        await nv.loadVolumes(volumes);

        // Configure view: multiplanar + 3D
        nv.setSliceType(nv.sliceTypeMultiplanar);
        if (typeof nv.setMultiplanarLayout === 'function') {
            nv.setMultiplanarLayout(2);
        }
        nv.opts.show3Dcrosshair = true;
        nv.setRenderAzimuthElevation(120, 10);
        nv.drawScene();

        console.log('[NiiVue] Viewer initialized successfully');

    } catch (error) {
        console.error('[NiiVue] Initialization error:', error);
        // Use textContent instead of innerHTML to prevent XSS
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'color:#f66;padding:20px;text-align:center;';
        errorDiv.textContent = 'Error loading viewer: ' + error.message;
        container.innerHTML = '';
        container.appendChild(errorDiv);
    }
})();
"""

# JavaScript code for event handlers (e.g. .then(js=...))
# This runs after Python updates the HTML value.
# ⚠️ CRITICAL: 'element' is NOT available here! Must use document.querySelector
#
# CRITICAL FIX (Issue #24): This code loads NiiVue DIRECTLY via dynamic import()
# from the data-niivue-url attribute. Same pattern as NIIVUE_ON_LOAD_JS.
NIIVUE_UPDATE_JS = """
(async () => {
    // We must find the container globally since 'element' is not available in event handlers
    const container = document.querySelector('.niivue-viewer');

    if (!container) {
        console.error('[NiiVue] Container not found');
        return;
    }

    const canvas = container.querySelector('canvas');
    const status = container.querySelector('.niivue-status');

    // Get URLs from data attributes
    const volumeUrl = container.dataset.volumeUrl;
    const maskUrl = container.dataset.maskUrl;
    const niivueUrl = container.dataset.niivueUrl;

    // Skip if no volume URL
    if (!volumeUrl) {
        return;
    }

    try {
        if (status) {
            status.style.display = 'block';
            status.innerText = 'Reloading viewer...';
        }

        // Check WebGL2 support
        const gl = canvas.getContext('webgl2');
        if (!gl) {
            container.innerHTML = '<div style="color:#fff;padding:20px;text-align:center;">WebGL2 not supported. Please use a modern browser.</div>';
            return;
        }

        // Load NiiVue directly (self-sufficient, no head= dependency)
        const loadNiivue = async () => {
            // Return cached if already loaded
            if (window.Niivue) {
                console.log('[NiiVue] Using cached window.Niivue');
                return window.Niivue;
            }

            // Load directly from the URL embedded in data attribute
            if (!niivueUrl) {
                throw new Error('No NiiVue URL provided in data-niivue-url attribute');
            }

            console.log('[NiiVue] Loading from:', niivueUrl);
            try {
                const module = await import(niivueUrl);
                window.Niivue = module.Niivue;
                console.log('[NiiVue] Successfully loaded and cached');
                return module.Niivue;
            } catch (e) {
                console.error('[NiiVue] Import failed:', e);
                throw new Error('Failed to load NiiVue from ' + niivueUrl + ': ' + e.message);
            }
        };

        const Niivue = await loadNiivue();

        // Initialize NiiVue
        const nv = new Niivue({
            logging: false,
            show3Dcrosshair: true,
            textHeight: 0.04,
            backColor: [0, 0, 0, 1],
            crosshairColor: [0.2, 0.8, 0.2, 1]
        });

        // Attach to canvas
        await nv.attachToCanvas(canvas);

        // Hide status message
        if (status) status.style.display = 'none';

        // Prepare volumes
        const volumes = [{ url: volumeUrl, name: 'input.nii.gz' }];

        if (maskUrl) {
            volumes.push({
                url: maskUrl,
                colorMap: 'red',
                opacity: 0.5
            });
        }

        // Load volumes
        await nv.loadVolumes(volumes);

        // Configure view: multiplanar + 3D
        nv.setSliceType(nv.sliceTypeMultiplanar);
        if (typeof nv.setMultiplanarLayout === 'function') {
            nv.setMultiplanarLayout(2);
        }
        nv.opts.show3Dcrosshair = true;
        nv.setRenderAzimuthElevation(120, 10);
        nv.drawScene();

        console.log('[NiiVue] Viewer re-initialized successfully via event handler');

    } catch (error) {
        console.error('[NiiVue] Re-initialization error:', error);
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'color:#f66;padding:20px;text-align:center;';
        errorDiv.textContent = 'Error reloading viewer: ' + error.message;
        if (container) {
            container.innerHTML = '';
            container.appendChild(errorDiv);
        }
    }
})();
"""
