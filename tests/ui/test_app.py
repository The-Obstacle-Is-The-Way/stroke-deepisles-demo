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

    # Mock list_case_ids to avoid network call
    with patch("stroke_deepisles_demo.ui.components.list_case_ids", return_value=["sub-001"]):
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


def test_run_segmentation_logic() -> None:
    """Test run_segmentation logic with mocks."""
    from stroke_deepisles_demo.pipeline import PipelineResult
    from stroke_deepisles_demo.ui.app import run_segmentation

    mock_result = PipelineResult(
        case_id="sub-001",
        input_files={"dwi": MagicMock(), "adc": MagicMock()},
        staged_dir=MagicMock(),
        prediction_mask=MagicMock(),
        ground_truth=MagicMock(),
        dice_score=0.85,
        elapsed_seconds=10.5,
    )

    # Mock everything that touches files/network
    with (
        patch("stroke_deepisles_demo.ui.app.run_pipeline_on_case", return_value=mock_result),
        patch("stroke_deepisles_demo.ui.app.nifti_to_data_url", return_value="data:image..."),
        patch("stroke_deepisles_demo.ui.app.create_niivue_html", return_value="<div></div>"),
        patch("stroke_deepisles_demo.ui.app.render_slice_comparison", return_value=MagicMock()),
    ):
        html, _fig, metrics, _dl_path, status = run_segmentation(
            "sub-001", fast_mode=True, show_ground_truth=True
        )

        assert html == "<div></div>"
        assert metrics["case_id"] == "sub-001"
        assert metrics["dice_score"] == 0.85
        assert "Success" in status
