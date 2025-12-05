"""Command-line interface for stroke-deepisles-demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stroke_deepisles_demo.data import list_case_ids
from stroke_deepisles_demo.pipeline import run_pipeline_on_case


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="stroke-demo",
        description="Run DeepISLES stroke segmentation on HF datasets",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    list_parser = subparsers.add_parser("list", help="List available cases")
    list_parser.add_argument("--dataset", default=None, help="HF dataset ID (not used yet)")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run segmentation")
    run_parser.add_argument("--case", type=str, help="Case ID (e.g., sub-stroke0001)")
    run_parser.add_argument("--index", type=int, help="Case index (alternative to --case)")
    run_parser.add_argument("--output", type=Path, default=None, help="Output directory")
    run_parser.add_argument(
        "--no-fast", action="store_false", dest="fast", help="Disable fast mode (SEALS-only)"
    )
    run_parser.set_defaults(fast=True)

    run_parser.add_argument("--no-gpu", action="store_true", help="Disable GPU")

    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list(args)
    elif args.command == "run":
        return cmd_run(args)

    return 0


def cmd_list(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Handle 'list' command."""
    try:
        case_ids = list_case_ids()
        print(f"Found {len(case_ids)} cases:")
        for i, cid in enumerate(case_ids):
            print(f"[{i}] {cid}")
        return 0
    except Exception as e:
        print(f"Error listing cases: {e}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Handle 'run' command."""
    if args.case is None and args.index is None:
        print("Error: Must specify --case or --index", file=sys.stderr)
        return 1

    case_id: str | int = args.case if args.case else args.index

    try:
        print(f"Running pipeline on case: {case_id} (fast={args.fast}, gpu={not args.no_gpu})")
        result = run_pipeline_on_case(
            case_id=case_id,
            output_dir=args.output,
            fast=args.fast,
            gpu=not args.no_gpu,
            compute_dice=True,
            cleanup_staging=True,  # Clean up by default for CLI runs
        )

        print("\nPipeline Completed Successfully!")
        print(f"Case ID: {result.case_id}")
        print(f"Prediction: {result.prediction_mask}")
        if result.ground_truth:
            print(f"Ground Truth: {result.ground_truth}")
            if result.dice_score is not None:
                print(f"Dice Score: {result.dice_score:.4f}")
        else:
            print("No Ground Truth available.")

        print(f"Elapsed: {result.elapsed_seconds:.1f}s")
        return 0

    except Exception as e:
        print(f"Pipeline failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
