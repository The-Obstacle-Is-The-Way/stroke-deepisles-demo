"""Main Gradio application for stroke-deepisles-demo."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import gradio as gr
from matplotlib.figure import Figure  # noqa: TC002

# CRITICAL: Allow direct file serving for local assets (niivue.js)
# This fixes the P0 "Loading..." bug on HF Spaces (Issue #11649)
# Must be called BEFORE creating any Blocks - hence imports after this call
_ASSETS_DIR = Path(__file__).parent / "assets"
gr.set_static_paths(paths=[str(_ASSETS_DIR)])

from stroke_deepisles_demo.core.logging import get_logger  # noqa: E402
from stroke_deepisles_demo.data import list_case_ids  # noqa: E402
from stroke_deepisles_demo.metrics import compute_volume_ml  # noqa: E402
from stroke_deepisles_demo.pipeline import run_pipeline_on_case  # noqa: E402
from stroke_deepisles_demo.ui.components import (  # noqa: E402
    create_case_selector,
    create_results_display,
    create_settings_accordion,
)
from stroke_deepisles_demo.ui.viewer import (  # noqa: E402
    NIIVUE_UPDATE_JS,
    create_niivue_html,
    get_niivue_loader_path,
    nifti_to_gradio_url,
    render_3panel_view,
    render_slice_comparison,
)

logger = get_logger(__name__)


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


def _cleanup_previous_results(previous_results_dir: str | None) -> None:
    """Clean up previous results directory (per-session, thread-safe)."""
    if previous_results_dir is None:
        return
    prev_path = Path(previous_results_dir)
    if prev_path.exists():
        try:
            shutil.rmtree(prev_path)
            logger.debug("Cleaned up previous results: %s", prev_path)
        except OSError as e:
            # Log but don't fail - cleanup is best-effort
            logger.warning("Failed to cleanup %s: %s", prev_path, e)


def run_segmentation(
    case_id: str,
    fast_mode: bool,
    show_ground_truth: bool,
    previous_results_dir: str | None,
) -> tuple[str, Figure | None, Figure | None, dict[str, Any], str | None, str, str | None]:
    """
    Run segmentation and return results for display.

    Args:
        case_id: Selected case identifier
        fast_mode: Whether to use fast mode (SEALS)
        show_ground_truth: Whether to show ground truth in plots
        previous_results_dir: Path to previous results (from gr.State, for cleanup)

    Returns:
        Tuple of (niivue_html, slice_fig, ortho_fig, metrics_dict, download_path, status_msg, new_results_dir)
        The new_results_dir is returned to update the gr.State for next cleanup.
    """
    if not case_id:
        return (
            "",
            None,
            None,
            {},
            None,
            "Please select a case first.",
            previous_results_dir,  # Keep existing state
        )

    try:
        # Clean up previous results (per-session, thread-safe via gr.State)
        _cleanup_previous_results(previous_results_dir)

        logger.info("Running segmentation for %s", case_id)
        result = run_pipeline_on_case(
            case_id,
            fast=fast_mode,
            compute_dice=True,
            cleanup_staging=True,
        )

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

        # 2. Static Visualizations (Matplotlib)
        gt_path = result.ground_truth if show_ground_truth else None

        # 2a. Slice Comparison
        slice_fig = render_slice_comparison(
            dwi_path=dwi_path,
            prediction_path=result.prediction_mask,
            ground_truth_path=gt_path,
            orientation="axial",
        )

        # 2b. Orthogonal 3-Panel View
        ortho_fig = render_3panel_view(
            nifti_path=dwi_path,
            mask_path=result.prediction_mask,
            mask_alpha=0.5,
        )

        # 3. Metrics (including volume with consistent 0.5 threshold)
        volume_ml: float | None = None
        try:
            volume_ml = round(compute_volume_ml(result.prediction_mask, threshold=0.5), 2)
        except Exception:
            logger.warning("Failed to compute volume for %s", case_id, exc_info=True)

        metrics = {
            "case_id": result.case_id,
            "dice_score": result.dice_score,
            "volume_ml": volume_ml,
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

        # Return new results_dir to update gr.State for next cleanup
        return (
            niivue_html,
            slice_fig,
            ortho_fig,
            metrics,
            download_path,
            status_msg,
            str(result.results_dir),
        )

    except Exception as e:
        logger.exception("Error running segmentation")
        return "", None, None, {}, None, f"Error: {e!s}", previous_results_dir


def create_app() -> gr.Blocks:
    """
    Create the Gradio application.

    Returns:
        Configured gr.Blocks application
    """
    with gr.Blocks(
        title="Stroke Lesion Segmentation Demo",
    ) as demo:
        # Per-session state for cleanup tracking (fixes race condition in multi-user env)
        # This replaces the previous global _previous_results_dir variable
        previous_results_state = gr.State(value=None)

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
                previous_results_state,  # Pass per-session state for cleanup
            ],
            outputs=[
                results["niivue_viewer"],
                results["slice_plot"],
                results["ortho_plot"],
                results["metrics"],
                results["download"],
                status,
                previous_results_state,  # Update state with new results_dir
            ],
        ).then(
            fn=None,  # JS-only handler to re-initialize NiiVue after HTML update
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

    # Generate the NiiVue loader HTML file (creates if needed)
    niivue_loader = get_niivue_loader_path()

    get_demo().launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=settings.gradio_share,
        theme=gr.themes.Soft(),
        css="footer {visibility: hidden}",
        show_error=True,  # Show full Python tracebacks in UI for debugging
        allowed_paths=[str(_ASSETS_DIR)],
        head_paths=[str(niivue_loader)],  # Official Gradio approach (Issue #11649)
    )
