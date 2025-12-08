"""Reusable UI components."""

from __future__ import annotations

import gradio as gr

from stroke_deepisles_demo.core.config import get_settings
from stroke_deepisles_demo.core.logging import get_logger

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
        # NiiVue visualization uses HTML
        niivue_viewer = gr.HTML(label="Interactive 3D Viewer")

        # Slice comparisons (Matplotlib)
        slice_plot = gr.Plot(label="Slice Comparison")

        metrics = gr.JSON(label="Metrics")
        download = gr.File(label="Download Prediction")

    return {
        "niivue_viewer": niivue_viewer,
        "slice_plot": slice_plot,
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
