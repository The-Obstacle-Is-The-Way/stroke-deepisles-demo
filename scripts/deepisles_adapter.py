#!/usr/bin/env python
"""DeepISLES adapter script for subprocess invocation.

This script runs inside the isles_ensemble conda environment (Python 3.8)
and is called by our Gradio app (Python 3.10+) via subprocess.

Usage:
    conda run -n isles_ensemble python scripts/deepisles_adapter.py \
        --dwi /path/to/dwi.nii.gz \
        --adc /path/to/adc.nii.gz \
        --output /path/to/output \
        [--flair /path/to/flair.nii.gz] \
        [--fast]

Note: This script intentionally uses Python 3.8 compatible syntax and
os.path functions (not pathlib) for compatibility with DeepISLES environment.
"""

import argparse
import os
import sys

# Add DeepISLES to path
sys.path.insert(0, "/app")

from src.isles22_ensemble import IslesEnsemble


def main() -> None:
    """Run DeepISLES inference with command-line arguments."""
    parser = argparse.ArgumentParser(description="DeepISLES inference adapter")
    parser.add_argument("--dwi", required=True, help="Path to DWI NIfTI file")
    parser.add_argument("--adc", required=True, help="Path to ADC NIfTI file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--flair", default=None, help="Path to FLAIR NIfTI file")
    parser.add_argument("--fast", action="store_true", help="Fast mode (SEALS only)")
    parser.add_argument("--ensemble-path", default="/app", help="Path to DeepISLES repo")

    args = parser.parse_args()

    # Validate inputs exist (using os.path for Py3.8 compatibility)
    if not os.path.exists(args.dwi):  # noqa: PTH110
        print(f"ERROR: DWI file not found: {args.dwi}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.adc):  # noqa: PTH110
        print(f"ERROR: ADC file not found: {args.adc}", file=sys.stderr)
        sys.exit(1)
    if args.flair and not os.path.exists(args.flair):  # noqa: PTH110
        print(f"ERROR: FLAIR file not found: {args.flair}", file=sys.stderr)
        sys.exit(1)

    # Create output directory (using os.makedirs for Py3.8 compatibility)
    os.makedirs(args.output, exist_ok=True)  # noqa: PTH103

    # Run inference
    print("Running DeepISLES inference...")
    print(f"  DWI: {args.dwi}")
    print(f"  ADC: {args.adc}")
    print(f"  FLAIR: {args.flair}")
    print(f"  Output: {args.output}")
    print(f"  Fast mode: {args.fast}")

    stroke_segm = IslesEnsemble()
    stroke_segm.predict_ensemble(
        ensemble_path=args.ensemble_path,
        input_dwi_path=args.dwi,
        input_adc_path=args.adc,
        input_flair_path=args.flair,
        output_path=args.output,
        fast=args.fast,
        skull_strip=False,
        save_team_outputs=False,
        results_mni=False,
        parallelize=True,
    )

    print(f"DeepISLES inference complete. Output: {args.output}")


if __name__ == "__main__":
    main()
