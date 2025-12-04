# phase 4: gradio / spaces app

## purpose

Build a minimal but clean Gradio 5 app that allows interactive case selection, segmentation, and visualization. At the end of this phase, we have a deployable Hugging Face Space.

## deliverables

- [ ] `src/stroke_deepisles_demo/ui/app.py` - Main Gradio application
- [ ] `src/stroke_deepisles_demo/ui/viewer.py` - NiiVue integration
- [ ] `src/stroke_deepisles_demo/ui/components.py` - Reusable UI components
- [ ] `app.py` at repo root - HF Spaces entry point
- [ ] Unit tests for UI logic (not Gradio itself)
- [ ] Smoke test for app import

## vertical slice outcome

After this phase, you can run locally:

```bash
uv run gradio src/stroke_deepisles_demo/ui/app.py
# or
uv run python -m stroke_deepisles_demo.ui.app
```

And deploy to Hugging Face Spaces with the standard Gradio SDK.

## module structure

```
src/stroke_deepisles_demo/ui/
├── __init__.py          # Public API
├── app.py               # Main Gradio application
├── viewer.py            # NiiVue integration
└── components.py        # Reusable UI components

# Root level for HF Spaces
app.py                   # Entry point: from stroke_deepisles_demo.ui.app import demo
```

## gradio 5 considerations

Based on [Gradio 5 documentation](https://huggingface.co/blog/gradio-5):

- Server-side rendering (SSR) for fast initial load
- Improved components (Buttons, Tabs, Sliders)
- WebRTC support for real-time streaming
- New built-in themes

Key patterns:
```python
import gradio as gr

# Gradio 5 app pattern
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Title")
    with gr.Row():
        with gr.Column():
            # Inputs
            ...
        with gr.Column():
            # Outputs
            ...

demo.launch()
```

## niivue integration strategy

[NiiVue](https://github.com/niivue/niivue) is a WebGL2-based neuroimaging viewer.

### proven implementation: tobias's bids-neuroimaging space

**Reference**: [TobiasPitters/bids-neuroimaging](https://huggingface.co/spaces/TobiasPitters/bids-neuroimaging) - A working HF Space with NiiVue multiplanar + 3D rendering.

Key patterns from Tobias's implementation:

1. **FastAPI + raw HTML** (not Gradio) - Cleaner for single-page viewer
2. **NiiVue via unpkg CDN**: `https://unpkg.com/@niivue/niivue@0.57.0/dist/index.js`
3. **Base64 data URLs** for NIfTI data (no file serving needed):
   ```python
   import base64
   nifti_bytes = nifti_image.to_bytes()
   nifti_b64 = base64.b64encode(nifti_bytes).decode("utf-8")
   data_url = f"data:application/octet-stream;base64,{nifti_b64}"
   ```
4. **NiiVue configuration for multiplanar + 3D**:
   ```javascript
   nv.setSliceType(nv.sliceTypeMultiplanar);
   nv.setMultiplanarLayout(2);  // 2x2 grid with 3D render
   nv.opts.show3Dcrosshair = true;
   ```

### recommended approach: hybrid fastapi + gradio

For our demo, we use a **hybrid approach**:
- **Gradio** for case selection dropdown and "Run Segmentation" button
- **FastAPI endpoints** for serving NIfTI data as base64
- **NiiVue via `gr.HTML`** for interactive 3D visualization

This gives us:
- Gradio's nice UI components for inputs
- Proven NiiVue rendering from Tobias's implementation
- No iframe complexity

### concrete implementation

```python
import base64
from pathlib import Path
import nibabel as nib

def nifti_to_data_url(nifti_path: Path) -> str:
    """Convert NIfTI file to base64 data URL for NiiVue."""
    img = nib.load(nifti_path)
    nifti_bytes = img.to_bytes()
    nifti_b64 = base64.b64encode(nifti_bytes).decode("utf-8")
    return f"data:application/octet-stream;base64,{nifti_b64}"

def create_niivue_viewer_html(
    volume_data_url: str,
    mask_data_url: str | None = None,
    height: int = 600,
) -> str:
    """Create NiiVue HTML viewer with optional mask overlay."""
    mask_loading = ""
    if mask_data_url:
        mask_loading = f"""
            volumes.push({{
                url: '{mask_data_url}',
                colorMap: 'red',
                opacity: 0.5
            }});
        """

    return f"""
    <div style="width:100%; height:{height}px; background:#000; border-radius:8px;">
        <canvas id="niivue-canvas" style="width:100%; height:100%;"></canvas>
    </div>
    <script type="module">
        const niivueModule = await import('https://unpkg.com/@niivue/niivue@0.57.0/dist/index.js');
        const Niivue = niivueModule.Niivue;

        const nv = new Niivue({{
            logging: false,
            show3Dcrosshair: true,
            textHeight: 0.04
        }});

        await nv.attachTo('niivue-canvas');

        const volumes = [{{
            url: '{volume_data_url}',
            name: 'dwi.nii.gz'
        }}];
        {mask_loading}

        await nv.loadVolumes(volumes);

        // Multiplanar + 3D view
        nv.setSliceType(nv.sliceTypeMultiplanar);
        if (nv.setMultiplanarLayout) {{
            nv.setMultiplanarLayout(2);
        }}
        nv.opts.show3Dcrosshair = true;
        nv.setRenderAzimuthElevation(120, 10);
        nv.drawScene();
    </script>
    """
```

### fallback: matplotlib 2d slices

For environments where WebGL fails, provide matplotlib fallback:

```python
import matplotlib.pyplot as plt
import nibabel as nib

def render_slices_fallback(nifti_path: Path, mask_path: Path | None = None) -> Figure:
    """Render 3-panel slice view with optional mask overlay."""
    img = nib.load(nifti_path)
    data = img.get_fdata()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Middle slices
    ax_slice = data.shape[2] // 2
    cor_slice = data.shape[1] // 2
    sag_slice = data.shape[0] // 2

    axes[0].imshow(data[:, :, ax_slice].T, cmap='gray', origin='lower')
    axes[0].set_title('Axial')
    axes[1].imshow(data[:, cor_slice, :].T, cmap='gray', origin='lower')
    axes[1].set_title('Coronal')
    axes[2].imshow(data[sag_slice, :, :].T, cmap='gray', origin='lower')
    axes[2].set_title('Sagittal')

    if mask_path:
        mask = nib.load(mask_path).get_fdata()
        # Overlay in red with alpha
        for ax, sl in zip(axes, [mask[:,:,ax_slice].T, mask[:,cor_slice,:].T, mask[sag_slice,:,:].T]):
            ax.imshow(sl, cmap='Reds', alpha=0.5, origin='lower')

    return fig
```

**Recommendation**: Use NiiVue as primary (proven working), matplotlib as fallback.

## interfaces and types

### `ui/app.py`

```python
"""Main Gradio application for stroke-deepisles-demo."""

from __future__ import annotations

import gradio as gr

from stroke_deepisles_demo.pipeline import run_pipeline_on_case
from stroke_deepisles_demo.ui.components import create_case_selector, create_results_display
from stroke_deepisles_demo.ui.viewer import render_comparison_view


def create_app() -> gr.Blocks:
    """
    Create the Gradio application.

    Returns:
        Configured gr.Blocks application
    """
    with gr.Blocks(
        title="Stroke Lesion Segmentation Demo",
        theme=gr.themes.Soft(),
    ) as demo:
        # Header
        gr.Markdown("""
        # Stroke Lesion Segmentation Demo

        This demo runs [DeepISLES](https://github.com/ezequieldlrosa/DeepIsles)
        stroke segmentation on cases from
        [ISLES24-MR-Lite](https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite).

        > **Disclaimer**: This is for research/demonstration only. Not for clinical use.
        """)

        with gr.Row():
            # Left column: Controls
            with gr.Column(scale=1):
                case_selector = create_case_selector()
                run_btn = gr.Button("Run Segmentation", variant="primary")
                status = gr.Textbox(label="Status", interactive=False)

            # Right column: Results
            with gr.Column(scale=2):
                results_display = create_results_display()

        # Event handlers
        run_btn.click(
            fn=run_segmentation,
            inputs=[case_selector],
            outputs=[results_display, status],
        )

    return demo


def run_segmentation(case_id: str) -> tuple[dict, str]:
    """
    Run segmentation and return results for display.

    Args:
        case_id: Selected case identifier

    Returns:
        Tuple of (results_dict, status_message)
    """
    ...


# Module-level app instance for Gradio CLI
demo = create_app()

if __name__ == "__main__":
    demo.launch()
```

### `ui/viewer.py`

```python
"""Neuroimaging visualization for Gradio."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from numpy.typing import NDArray


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
        slice_idx: Slice index (default: middle slice)
        orientation: One of "axial", "coronal", "sagittal"

    Returns:
        Matplotlib figure with comparison view
    """
    ...


def render_3panel_view(
    nifti_path: Path,
    mask_path: Path | None = None,
    *,
    mask_alpha: float = 0.5,
    mask_color: str = "red",
) -> Figure:
    """
    Render axial/coronal/sagittal slices with optional mask overlay.

    Args:
        nifti_path: Path to base NIfTI volume
        mask_path: Optional path to mask for overlay
        mask_alpha: Transparency of mask overlay
        mask_color: Color for mask overlay

    Returns:
        Matplotlib figure with 3-panel view
    """
    ...


def create_niivue_html(
    volume_url: str,
    mask_url: str | None = None,
    *,
    height: int = 400,
) -> str:
    """
    Create HTML/JS for NiiVue viewer.

    Args:
        volume_url: URL to volume NIfTI file
        mask_url: Optional URL to mask NIfTI file
        height: Viewer height in pixels

    Returns:
        HTML string with embedded NiiVue viewer
    """
    template = f"""
    <div id="gl" style="width:100%; height:{height}px;"></div>
    <script type="module">
        import {{ Niivue }} from 'https://niivue.github.io/niivue/features/niivue.esm.js';
        const nv = new Niivue({{ show3Dcrosshair: true }});
        nv.attachToCanvas(document.getElementById('gl'));
        const volumes = [{{ url: '{volume_url}' }}];
        {'volumes.push({ url: "' + mask_url + '", colorMap: "red", opacity: 0.5 });' if mask_url else ''}
        await nv.loadVolumes(volumes);
    </script>
    """
    return template


def get_slice_at_max_lesion(
    mask_path: Path,
    orientation: str = "axial",
) -> int:
    """
    Find slice index with maximum lesion area.

    Useful for displaying the most informative slice.

    Args:
        mask_path: Path to lesion mask NIfTI
        orientation: Slice orientation

    Returns:
        Slice index with maximum lesion area
    """
    ...
```

### `ui/components.py`

```python
"""Reusable UI components."""

from __future__ import annotations

import gradio as gr

from stroke_deepisles_demo.data import list_case_ids


def create_case_selector() -> gr.Dropdown:
    """
    Create a dropdown for selecting cases.

    Returns:
        Configured gr.Dropdown component
    """
    try:
        case_ids = list_case_ids()
    except Exception:
        case_ids = ["Error loading cases"]

    return gr.Dropdown(
        choices=case_ids,
        value=case_ids[0] if case_ids else None,
        label="Select Case",
        info="Choose a case from ISLES24-MR-Lite",
    )


def create_results_display() -> dict[str, gr.components.Component]:
    """
    Create results display components.

    Returns:
        Dictionary of component name -> gr.Component
    """
    with gr.Group():
        viewer = gr.Image(label="Segmentation Result", type="filepath")
        metrics = gr.JSON(label="Metrics")
        download = gr.File(label="Download Prediction")

    return {
        "viewer": viewer,
        "metrics": metrics,
        "download": download,
    }


def create_settings_accordion() -> dict[str, gr.components.Component]:
    """
    Create expandable settings section.

    Returns:
        Dictionary of setting name -> gr.Component
    """
    with gr.Accordion("Advanced Settings", open=False):
        fast_mode = gr.Checkbox(
            value=True,
            label="Fast Mode",
            info="Use single model (faster, slightly less accurate)",
        )
        show_ground_truth = gr.Checkbox(
            value=True,
            label="Show Ground Truth",
            info="Display ground truth mask if available",
        )

    return {
        "fast_mode": fast_mode,
        "show_ground_truth": show_ground_truth,
    }
```

### Root `app.py` for HF Spaces

```python
"""Entry point for Hugging Face Spaces deployment."""

from stroke_deepisles_demo.ui.app import demo

if __name__ == "__main__":
    demo.launch()
```

## hugging face spaces configuration

### `README.md` header for Spaces

```yaml
---
title: Stroke DeepISLES Demo
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 5.0.0
app_file: app.py
pinned: false
license: mit
---
```

### `requirements.txt` for Spaces

```
# Note: HF Spaces uses requirements.txt, not pyproject.toml
git+https://github.com/CloseChoice/datasets.git@feat/bids-loader-streaming-upload-fix
huggingface-hub>=0.25.0
nibabel>=5.2.0
numpy>=1.26.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
gradio>=5.0.0
matplotlib>=3.8.0
```

## tdd plan

### test file structure

```
tests/
├── ui/
│   ├── __init__.py
│   ├── test_viewer.py       # Tests for visualization
│   ├── test_components.py   # Tests for UI components
│   └── test_app.py          # Smoke tests for app
```

### tests to write first (TDD order)

#### 1. `tests/ui/test_viewer.py` - Pure visualization functions

```python
"""Tests for viewer module."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")  # Non-interactive backend for tests

from stroke_deepisles_demo.ui.viewer import (
    create_niivue_html,
    get_slice_at_max_lesion,
    render_3panel_view,
    render_slice_comparison,
)


class TestRender3PanelView:
    """Tests for render_3panel_view."""

    def test_returns_matplotlib_figure(self, synthetic_nifti_3d: Path) -> None:
        """Returns a matplotlib Figure object."""
        fig = render_3panel_view(synthetic_nifti_3d)

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_has_three_axes(self, synthetic_nifti_3d: Path) -> None:
        """Figure has 3 subplots (axial, coronal, sagittal)."""
        fig = render_3panel_view(synthetic_nifti_3d)

        assert len(fig.axes) == 3
        plt.close(fig)

    def test_overlay_mask_when_provided(
        self, synthetic_nifti_3d: Path, temp_dir: Path
    ) -> None:
        """Overlays mask when mask_path provided."""
        # Create a simple mask
        import nibabel as nib

        mask_data = np.zeros((10, 10, 10), dtype=np.uint8)
        mask_data[4:6, 4:6, 4:6] = 1
        mask_img = nib.Nifti1Image(mask_data, np.eye(4))
        mask_path = temp_dir / "mask.nii.gz"
        nib.save(mask_img, mask_path)

        fig = render_3panel_view(synthetic_nifti_3d, mask_path=mask_path)

        # Should not raise
        assert fig is not None
        plt.close(fig)


class TestRenderSliceComparison:
    """Tests for render_slice_comparison."""

    def test_comparison_without_ground_truth(
        self, synthetic_nifti_3d: Path
    ) -> None:
        """Works when ground truth is None."""
        fig = render_slice_comparison(
            synthetic_nifti_3d,
            synthetic_nifti_3d,  # Use same as prediction for test
            ground_truth_path=None,
        )

        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_comparison_with_ground_truth(
        self, synthetic_nifti_3d: Path
    ) -> None:
        """Works when ground truth is provided."""
        fig = render_slice_comparison(
            synthetic_nifti_3d,
            synthetic_nifti_3d,
            ground_truth_path=synthetic_nifti_3d,
        )

        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestGetSliceAtMaxLesion:
    """Tests for get_slice_at_max_lesion."""

    def test_finds_slice_with_lesion(self, temp_dir: Path) -> None:
        """Returns slice index where lesion is largest."""
        import nibabel as nib

        # Create mask with lesion at slice 7
        mask_data = np.zeros((10, 10, 10), dtype=np.uint8)
        mask_data[:, :, 7] = 1  # Full slice 7 is lesion

        mask_img = nib.Nifti1Image(mask_data, np.eye(4))
        mask_path = temp_dir / "mask.nii.gz"
        nib.save(mask_img, mask_path)

        slice_idx = get_slice_at_max_lesion(mask_path, orientation="axial")

        assert slice_idx == 7

    def test_returns_middle_for_empty_mask(self, temp_dir: Path) -> None:
        """Returns middle slice when mask is empty."""
        import nibabel as nib

        mask_data = np.zeros((10, 10, 20), dtype=np.uint8)
        mask_img = nib.Nifti1Image(mask_data, np.eye(4))
        mask_path = temp_dir / "mask.nii.gz"
        nib.save(mask_img, mask_path)

        slice_idx = get_slice_at_max_lesion(mask_path, orientation="axial")

        assert slice_idx == 10  # Middle of 20


class TestCreateNiivueHtml:
    """Tests for create_niivue_html."""

    def test_includes_volume_url(self) -> None:
        """Generated HTML includes the volume URL."""
        html = create_niivue_html("http://example.com/brain.nii.gz")

        assert "http://example.com/brain.nii.gz" in html

    def test_includes_mask_when_provided(self) -> None:
        """Generated HTML includes mask URL when provided."""
        html = create_niivue_html(
            "http://example.com/brain.nii.gz",
            mask_url="http://example.com/mask.nii.gz",
        )

        assert "http://example.com/mask.nii.gz" in html

    def test_sets_height(self) -> None:
        """Generated HTML respects height parameter."""
        html = create_niivue_html(
            "http://example.com/brain.nii.gz",
            height=600,
        )

        assert "height:600px" in html
```

#### 2. `tests/ui/test_app.py` - Smoke tests

```python
"""Smoke tests for Gradio app."""

from __future__ import annotations


def test_app_module_imports() -> None:
    """App module imports without side effects."""
    # This should not launch the app or make network calls
    from stroke_deepisles_demo.ui import app

    assert hasattr(app, "create_app")
    assert hasattr(app, "demo")


def test_create_app_returns_blocks() -> None:
    """create_app returns a gr.Blocks instance."""
    import gradio as gr

    from stroke_deepisles_demo.ui.app import create_app

    app = create_app()

    assert isinstance(app, gr.Blocks)


def test_viewer_module_imports() -> None:
    """Viewer module imports without errors."""
    from stroke_deepisles_demo.ui import viewer

    assert hasattr(viewer, "render_3panel_view")
    assert hasattr(viewer, "create_niivue_html")


def test_components_module_imports() -> None:
    """Components module imports without errors."""
    from stroke_deepisles_demo.ui import components

    assert hasattr(components, "create_case_selector")
    assert hasattr(components, "create_results_display")
```

### what to mock

- `list_case_ids()` in components - Avoid network during import
- Any data loading in app initialization

### what to test for real

- Matplotlib figure generation
- NiiVue HTML string generation
- Slice finding algorithms
- Module imports (no network side effects)

## "done" criteria

Phase 4 is complete when:

1. All unit tests pass: `uv run pytest tests/ui/ -v`
2. App launches locally: `uv run python -m stroke_deepisles_demo.ui.app`
3. Can select a case, click "Run", see visualization
4. Visualization shows DWI with predicted mask overlay
5. Metrics (Dice score) displayed
6. Type checking passes: `uv run mypy src/stroke_deepisles_demo/ui/`
7. Ready for HF Spaces deployment (README header, requirements.txt)

## implementation notes

- **NiiVue is primary** - Proven working in Tobias's Space, not "fragile"
- **Base64 data URLs** - Avoids file serving complexity, works in all environments
- **Lazy initialization** - Do NOT call `list_case_ids()` at module import time (causes network calls)
- **Test on HF Spaces early** - Verify WebGL works in their environment
- **Keep UI simple** - This is a demo, not a full application
- **Cache case list** - Avoid repeated HF Hub calls

### avoiding import-time side effects

The reviewer correctly noted that `demo = create_app()` at module level triggers network calls. Fix:

```python
# BAD - triggers network call on import
demo = create_app()

# GOOD - lazy initialization
_demo: gr.Blocks | None = None

def get_demo() -> gr.Blocks:
    global _demo
    if _demo is None:
        _demo = create_app()
    return _demo

# For Gradio CLI compatibility
demo = None  # Set lazily

if __name__ == "__main__":
    get_demo().launch()
```

Or use a factory pattern in the root `app.py`:

```python
# app.py (HF Spaces entry point)
from stroke_deepisles_demo.ui.app import create_app

demo = create_app()  # Only called when this file is executed

if __name__ == "__main__":
    demo.launch()
```

## dependencies to add

```toml
# Add to pyproject.toml dependencies
"matplotlib>=3.8.0",
"fastapi>=0.115.0",  # For API endpoints if using hybrid approach
"uvicorn[standard]>=0.32.0",  # For local development
```

## reference implementation

Clone Tobias's working Space for reference:
```
_reference_repos/bids-neuroimaging-space/
```

Key file: `main.py` - Complete NiiVue + FastAPI implementation.
