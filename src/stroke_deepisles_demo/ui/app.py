"""Main Gradio application for stroke-deepisles-demo."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

import gradio as gr
from matplotlib.figure import Figure  # noqa: TC002

from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.data import list_case_ids
from stroke_deepisles_demo.pipeline import run_pipeline_on_case
from stroke_deepisles_demo.ui.components import (
    create_case_selector,
    create_results_display,
    create_settings_accordion,
)
from stroke_deepisles_demo.ui.viewer import (
    NIIVUE_UPDATE_JS,
    create_niivue_html,
    nifti_to_gradio_url,
    render_slice_comparison,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

# Shared output directory for UI results (cleaned up between runs to prevent disk accumulation)
_previous_results_dir: Path | None = None


def initialize_case_selector() -> gr.Dropdown:
    """
    Initialize case selector by loading dataset (lazy load).

    This prevents the app from hanging during startup while downloading data.
    Called via demo.load() after the UI renders.
    """
    try:
        logger.info("Initializing dataset for case selector...")
        case_ids = list_case_ids()

        if not case_ids:
            return gr.Dropdown(choices=[], info="No cases found in dataset.")

        return gr.Dropdown(
            choices=case_ids,
            value=case_ids[0],
            info="Choose a case from isles24-stroke dataset",
            interactive=True,
        )
    except Exception as e:
        logger.exception("Failed to initialize dataset")
        return gr.Dropdown(choices=[], info=f"Error loading data: {e!s}")


def run_segmentation(
    case_id: str, fast_mode: bool, show_ground_truth: bool
) -> tuple[str, Figure | None, dict[str, Any], str | None, str]:
    """
    Run segmentation and return results for display.

    Args:
        case_id: Selected case identifier
        fast_mode: Whether to use fast mode (SEALS)
        show_ground_truth: Whether to show ground truth in plots

    Returns:
        Tuple of (niivue_html, slice_fig, metrics_dict, download_path, status_msg)
    """
    if not case_id:
        return (
            "",
            None,
            {},
            None,
            "Please select a case first.",
        )

    try:
        global _previous_results_dir

        # Clean up previous results to prevent disk accumulation on HF Spaces
        if _previous_results_dir is not None and _previous_results_dir.exists():
            try:
                shutil.rmtree(_previous_results_dir)
                logger.debug("Cleaned up previous results: %s", _previous_results_dir)
            except OSError as e:
                # Log but don't fail - cleanup is best-effort
                logger.warning("Failed to cleanup %s: %s", _previous_results_dir, e)

        logger.info("Running segmentation for %s", case_id)
        result = run_pipeline_on_case(
            case_id,
            fast=fast_mode,
            compute_dice=True,
            cleanup_staging=True,
        )

        # Track results_dir for cleanup on next run
        _previous_results_dir = result.results_dir

        # 1. NiiVue Visualization
        # Use Gradio's file serving (Issue #19 optimization)
        # This eliminates ~65MB base64 payloads, improving load times and browser memory
        # Files in tempfile.gettempdir() are accessible via /gradio_api/file= by default
        dwi_path = result.input_files["dwi"]
        dwi_url = nifti_to_gradio_url(dwi_path)

        # prediction_mask is always a valid Path from the pipeline (not Optional)
        # The .exists() check is defense-in-depth only
        mask_url = None
        if result.prediction_mask.exists():
            mask_url = nifti_to_gradio_url(result.prediction_mask)

        niivue_html = create_niivue_html(
            dwi_url,
            mask_url,
            height=500,
        )

        # 2. Slice Comparison (Static Plot)
        gt_path = result.ground_truth if show_ground_truth else None
        slice_fig = render_slice_comparison(
            dwi_path=dwi_path,
            prediction_path=result.prediction_mask,
            ground_truth_path=gt_path,
            orientation="axial",
        )

        # 3. Metrics
        metrics = {
            "case_id": result.case_id,
            "dice_score": result.dice_score,
            "elapsed_seconds": round(result.elapsed_seconds, 2),
            "model": "SEALS (Fast)" if fast_mode else "Ensemble",
        }

        # 4. Download
        download_path = str(result.prediction_mask)

        status_msg = (
            f"Success! Dice: {result.dice_score:.3f}"
            if result.dice_score is not None
            else "Success!"
        )

        return niivue_html, slice_fig, metrics, download_path, status_msg

    except Exception as e:
        logger.exception("Error running segmentation")
        return "", None, {}, None, f"Error: {e!s}"


def create_app() -> gr.Blocks:
    """
    Create the Gradio application.

    Returns:
        Configured gr.Blocks application
    """
    with gr.Blocks(
        title="Stroke Lesion Segmentation Demo",
    ) as demo:
        # Header
        gr.Markdown("""
        # Stroke Lesion Segmentation Demo

        This demo runs [DeepISLES](https://github.com/ezequieldlrosa/DeepIsles)
        stroke segmentation on cases from
        [isles24-stroke](https://huggingface.co/datasets/hugging-science/isles24-stroke).

        **Model:** SEALS (ISLES'22 winner) - Fast, accurate ischemic stroke lesion segmentation.

        **Note:** First run may take a moment to load models and data.
        """)

        with gr.Row():
            # Left column: Controls
            with gr.Column(scale=1):
                case_selector = create_case_selector()
                settings = create_settings_accordion()
                run_btn = gr.Button("Run Segmentation", variant="primary")
                status = gr.Textbox(label="Status", interactive=False)

            # Right column: Results
            with gr.Column(scale=2):
                results = create_results_display()

        # Event handlers
        run_btn.click(
            fn=run_segmentation,
            inputs=[
                case_selector,
                settings["fast_mode"],
                settings["show_ground_truth"],
            ],
            outputs=[
                results["niivue_viewer"],
                results["slice_plot"],
                results["metrics"],
                results["download"],
                status,
            ],
        ).then(
            fn=None,  # Explicitly None to run JS only
            js=NIIVUE_UPDATE_JS,
        )

        # Trigger data loading after UI renders (prevents startup timeout)
        demo.load(initialize_case_selector, outputs=[case_selector])

    return demo  # type: ignore[no-any-return]


# Lazy initialization pattern
_demo: gr.Blocks | None = None


def get_demo() -> gr.Blocks:
    """Get the global demo instance, creating it if necessary."""
    global _demo
    if _demo is None:
        _demo = create_app()
    return _demo


if __name__ == "__main__":
    from stroke_deepisles_demo.core.config import get_settings
    from stroke_deepisles_demo.core.logging import setup_logging

    settings = get_settings()
    setup_logging(settings.log_level, format_style=settings.log_format)

    get_demo().launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=settings.gradio_share,
        theme=gr.themes.Soft(),
        css="footer {visibility: hidden}",
        show_error=True,  # Show full Python tracebacks in UI for debugging
    )
