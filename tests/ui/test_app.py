"""Smoke tests for Gradio app."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_app_module_imports() -> None:
    """App module imports without side effects."""
    # This should not launch the app or make network calls
    from stroke_deepisles_demo.ui import app

    assert hasattr(app, "create_app")
    assert hasattr(app, "get_demo")


def test_create_app_returns_blocks() -> None:
    """create_app returns a gr.Blocks instance."""
    import gradio as gr

    from stroke_deepisles_demo.ui.app import create_app

    # No mock needed - create_case_selector is now lazy (empty dropdown)
    # Data loading happens via demo.load() after UI renders
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


def test_run_segmentation_logic() -> None:
    """Test run_segmentation logic with mocks."""
    from stroke_deepisles_demo.pipeline import PipelineResult
    from stroke_deepisles_demo.ui.app import run_segmentation

    mock_result = PipelineResult(
        case_id="sub-001",
        input_files={"dwi": MagicMock(), "adc": MagicMock()},
        results_dir=MagicMock(),
        prediction_mask=MagicMock(),
        ground_truth=MagicMock(),
        dice_score=0.85,
        elapsed_seconds=10.5,
    )

    # Mock everything that touches files/network
    with (
        patch("stroke_deepisles_demo.ui.app.run_pipeline_on_case", return_value=mock_result),
        patch(
            "stroke_deepisles_demo.ui.app.nifti_to_gradio_url",
            return_value="/gradio_api/file=/tmp/test.nii.gz",
        ),
        patch("stroke_deepisles_demo.ui.app.create_niivue_html", return_value="<div></div>"),
        patch("stroke_deepisles_demo.ui.app.render_slice_comparison", return_value=MagicMock()),
        patch("stroke_deepisles_demo.ui.app.render_3panel_view", return_value=MagicMock()),
        patch("stroke_deepisles_demo.ui.app.compute_volume_ml", return_value=15.5),
    ):
        html, _fig, _ortho, metrics, _dl_path, status, _new_results_dir = run_segmentation(
            "sub-001",
            fast_mode=True,
            show_ground_truth=True,
            previous_results_dir=None,  # No previous results in test
        )

        assert html == "<div></div>"
        assert metrics["case_id"] == "sub-001"
        assert metrics["dice_score"] == 0.85
        assert "volume_ml" in metrics  # New metric added
        assert "Success" in status
