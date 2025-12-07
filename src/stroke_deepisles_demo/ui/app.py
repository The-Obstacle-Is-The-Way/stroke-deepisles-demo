"""Main Gradio application for stroke-deepisles-demo."""

from __future__ import annotations

from typing import Any

import gradio as gr
from matplotlib.figure import Figure  # noqa: TC002

from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.pipeline import run_pipeline_on_case
from stroke_deepisles_demo.ui.components import (
    create_case_selector,
    create_results_display,
    create_settings_accordion,
)
from stroke_deepisles_demo.ui.viewer import (
    create_niivue_html,
    nifti_to_data_url,
    render_slice_comparison,
)

logger = get_logger(__name__)


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
        logger.info("Running segmentation for %s", case_id)
        result = run_pipeline_on_case(
            case_id,
            fast=fast_mode,
            compute_dice=True,
            cleanup_staging=True,
        )

        # 1. NiiVue Visualization
        # We need data URLs for the browser
        # Note: This reads the file content into memory (base64)
        # For large datasets, this might be heavy, but for ISLES24-MR-Lite (cropped) it's fine.
        # Assuming DWI is the background
        dwi_path = result.input_files["dwi"]
        dwi_url = nifti_to_data_url(dwi_path)

        mask_url = None
        if result.prediction_mask and result.prediction_mask.exists():
            mask_url = nifti_to_data_url(result.prediction_mask)

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
        [ISLES24-MR-Lite](https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite).

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
        )

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
    )
