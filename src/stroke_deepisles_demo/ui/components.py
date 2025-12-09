"""Reusable UI components."""

from __future__ import annotations

import gradio as gr

from stroke_deepisles_demo.core.config import get_settings
from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.ui.viewer import NIIVUE_ON_LOAD_JS

logger = get_logger(__name__)


def create_case_selector() -> gr.Dropdown:
    """
    Create a dropdown for selecting cases.

    Initially empty; populated by app load event to prevent blocking startup.

    Returns:
        Configured gr.Dropdown component
    """
    return gr.Dropdown(
        choices=[],
        value=None,
        label="Select Case",
        info="Initializing dataset... please wait.",
        filterable=True,
        interactive=True,
    )


def create_results_display() -> dict[str, gr.components.Component]:
    """
    Create results display components.

    Returns:
        Dictionary of component name -> gr.Component
    """
    # Using gr.Group to group them visually
    with gr.Group():
        with gr.Tabs():
            with gr.Tab("Interactive 3D"):
                # NiiVue visualization uses HTML with js_on_load for JavaScript execution
                # Note: Gradio strips <script> tags from HTML value for security,
                # so we must use js_on_load to run our NiiVue initialization code.
                # The HTML value contains data-* attributes with volume URLs.
                niivue_viewer = gr.HTML(
                    label="Interactive 3D Viewer",
                    js_on_load=NIIVUE_ON_LOAD_JS,
                )

            with gr.Tab("Static Report"):
                # Slice comparisons (Matplotlib)
                slice_plot = gr.Plot(label="Slice Comparison (Validation)")
                ortho_plot = gr.Plot(label="Orthogonal Views (Anatomy)")

        metrics = gr.JSON(label="Metrics")
        download = gr.File(label="Download Prediction")

    return {
        "niivue_viewer": niivue_viewer,
        "slice_plot": slice_plot,
        "ortho_plot": ortho_plot,
        "metrics": metrics,
        "download": download,
    }


def create_settings_accordion() -> dict[str, gr.components.Component]:
    """
    Create expandable settings section.

    Returns:
        Dictionary of setting name -> gr.Component
    """
    settings = get_settings()

    with gr.Accordion("Advanced Settings", open=False):
        fast_mode = gr.Checkbox(
            value=settings.deepisles_fast_mode,
            label="Fast Mode (SEALS)",
            info="Run SEALS only (ISLES'22 winner, requires DWI+ADC). Disable for full ensemble (requires FLAIR).",
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
