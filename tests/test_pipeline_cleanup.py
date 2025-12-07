from pathlib import Path
from unittest.mock import MagicMock, patch

from stroke_deepisles_demo.pipeline import run_pipeline_on_case


def test_pipeline_cleanup_default() -> None:
    """Test that pipeline cleans up staging directory by default."""

    # Mock everything to avoid running actual heavy inference
    with (
        patch("stroke_deepisles_demo.pipeline.load_isles_dataset") as mock_load,
        patch("stroke_deepisles_demo.pipeline.stage_case_for_deepisles") as mock_stage,
        patch("stroke_deepisles_demo.pipeline.run_deepisles_on_folder") as mock_run,
        patch("stroke_deepisles_demo.pipeline.metrics.compute_dice"),
        patch("shutil.rmtree") as mock_rmtree,
    ):
        # Setup mocks
        mock_dataset = MagicMock()
        mock_load.return_value = mock_dataset
        mock_dataset.list_case_ids.return_value = ["case1"]
        mock_dataset.get_case.return_value = {"dwi": Path("dwi.nii.gz")}

        mock_staged = MagicMock()
        mock_staged.input_dir = Path("/tmp/mock_staging")
        mock_stage.return_value = mock_staged

        mock_result = MagicMock()
        mock_result.prediction_mask = Path("/tmp/results/pred.nii.gz")
        mock_run.return_value = mock_result

        # Run pipeline with defaults (cleanup_staging=True is the default)
        run_pipeline_on_case("case1")

        # Verify that rmtree was called
        assert mock_rmtree.called

        # Get the path passed to stage_case_for_deepisles
        # call_args[0][1] is the second positional arg: staging_root
        args, _ = mock_stage.call_args
        staging_root_passed = args[1]

        # Verify rmtree was called with that same path
        mock_rmtree.assert_called_with(staging_root_passed, ignore_errors=True)
