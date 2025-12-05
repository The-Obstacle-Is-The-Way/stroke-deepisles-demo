"""Tests for CLI."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from stroke_deepisles_demo.cli import main
from stroke_deepisles_demo.pipeline import PipelineResult


class TestCli:
    """Tests for CLI entry point."""

    def test_list_command(self) -> None:
        """List command prints cases."""
        with (
            patch("stroke_deepisles_demo.cli.list_case_ids", return_value=["sub-001"]),
            patch("builtins.print") as mock_print,
        ):
            exit_code = main(["list"])
            assert exit_code == 0
            mock_print.assert_called()

    def test_run_command_by_index(self) -> None:
        """Run command with index calls pipeline."""
        result = PipelineResult(
            case_id="sub-001",
            input_files=MagicMock(),
            staged_dir=MagicMock(),
            prediction_mask=MagicMock(),
            ground_truth=None,
            dice_score=None,
            elapsed_seconds=10.0,
        )

        with patch(
            "stroke_deepisles_demo.cli.run_pipeline_on_case", return_value=result
        ) as mock_run:
            exit_code = main(["run", "--index", "0"])
            assert exit_code == 0

            mock_run.assert_called_once()
            kwargs = mock_run.call_args.kwargs
            assert kwargs["case_id"] == 0
            assert kwargs["fast"] is True  # Default
            assert kwargs["gpu"] is True  # Default

    def test_run_command_by_id_no_gpu(self) -> None:
        """Run command with ID and no-gpu flag."""
        result = PipelineResult(
            case_id="sub-001",
            input_files=MagicMock(),
            staged_dir=MagicMock(),
            prediction_mask=MagicMock(),
            ground_truth=None,
            dice_score=None,
            elapsed_seconds=10.0,
        )

        with patch(
            "stroke_deepisles_demo.cli.run_pipeline_on_case", return_value=result
        ) as mock_run:
            exit_code = main(["run", "--case", "sub-001", "--no-gpu"])
            assert exit_code == 0

            kwargs = mock_run.call_args.kwargs
            assert kwargs["case_id"] == "sub-001"
            assert kwargs["gpu"] is False

    def test_run_command_fails_without_arg(self) -> None:
        """Run command fails if no case specified."""
        with patch("builtins.print"):  # Suppress error output
            exit_code = main(["run"])
            assert exit_code == 1
