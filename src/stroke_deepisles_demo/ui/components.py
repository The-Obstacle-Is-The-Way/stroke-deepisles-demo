"""Reusable UI components."""

from __future__ import annotations

import gradio as gr

from stroke_deepisles_demo.core.config import get_settings
from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.data import list_case_ids

logger = get_logger(__name__)


def create_case_selector() -> gr.Dropdown:
    """
    Create a dropdown for selecting cases.

    Returns:
        Configured gr.Dropdown component

    Raises:
        RuntimeError: If case IDs cannot be loaded (no silent fallback)
    """
    try:
        case_ids = list_case_ids()
    except FileNotFoundError as e:
        # Data directory not found - fail loudly with helpful message
        logger.error("Data directory not found: %s", e)
        raise RuntimeError("ISLES24 data not found. Please run: uv run stroke-demo download") from e
    except Exception as e:
        # Unexpected error - fail loudly, don't mask with fake dropdown option
        logger.exception("Failed to load case IDs")
        raise RuntimeError(f"Failed to load case IDs: {e}") from e

    if not case_ids:
        raise RuntimeError("No cases found in dataset. Please verify data directory structure.")

    return gr.Dropdown(
        choices=case_ids,
        value=case_ids[0],
        label="Select Case",
        info="Choose a case from ISLES24-MR-Lite",
        filterable=True,
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
