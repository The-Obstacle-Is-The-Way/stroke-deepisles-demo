from pathlib import Path
from unittest.mock import MagicMock, patch

from stroke_deepisles_demo.pipeline import run_pipeline_on_case


def test_pipeline_cleanup_default(temp_dir: Path) -> None:
    """Test that pipeline cleans up staging directory by default."""
    # Create real files (pipeline now copies input files to results_dir)
    dwi_file = temp_dir / "dwi.nii.gz"
    dwi_file.write_bytes(b"fake dwi")
    adc_file = temp_dir / "adc.nii.gz"
    adc_file.write_bytes(b"fake adc")

    # Mock everything to avoid running actual heavy inference
    with (
        patch("stroke_deepisles_demo.pipeline.load_isles_dataset") as mock_load,
        patch("stroke_deepisles_demo.pipeline.stage_case_for_deepisles") as mock_stage,
        patch("stroke_deepisles_demo.pipeline.run_deepisles_on_folder") as mock_run,
        patch("stroke_deepisles_demo.pipeline.metrics.compute_dice"),
        patch("stroke_deepisles_demo.pipeline.shutil.rmtree") as mock_rmtree,
    ):
        # Setup mocks
        mock_dataset = MagicMock()
        mock_dataset.list_case_ids.return_value = ["case1"]
        # Return dict with real files (no ground_truth)
        mock_dataset.get_case.return_value = {"dwi": dwi_file, "adc": adc_file}

        # Support context manager protocol: with load_isles_dataset() as dataset:
        mock_load.return_value.__enter__ = MagicMock(return_value=mock_dataset)
        mock_load.return_value.__exit__ = MagicMock(return_value=None)

        mock_staged = MagicMock()
        mock_staged.input_dir = Path("/tmp/mock_staging")
        mock_stage.return_value = mock_staged

        mock_result = MagicMock()
        mock_result.prediction_mask = Path("/tmp/results/pred.nii.gz")
        mock_run.return_value = mock_result

        # Run pipeline with defaults (cleanup_staging=True is the default)
        run_pipeline_on_case("case1")

        # Verify that rmtree was called (for staging cleanup)
        assert mock_rmtree.called

        # Get the path passed to stage_case_for_deepisles
        # call_args[0][1] is the second positional arg: staging_root
        args, _ = mock_stage.call_args
        staging_root_passed = args[1]

        # Verify rmtree was called with that same path
        mock_rmtree.assert_called_with(staging_root_passed, ignore_errors=True)
