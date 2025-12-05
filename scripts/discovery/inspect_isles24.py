#!/usr/bin/env python3
"""
ISLES24-MR-Lite Dataset Discovery Script

Downloads and inspects the full YongchengYAO/ISLES24-MR-Lite dataset
to document its exact schema before building adapters.

Per: docs/specs/data-discovery.md

Output: data/scratch/isles24_schema_report.txt
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
DATASET_ID = "YongchengYAO/ISLES24-MR-Lite"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "scratch"
REPORT_FILE = OUTPUT_DIR / "isles24_schema_report.txt"


def safe_type_name(val: Any) -> str:
    """Get a safe string representation of a value's type."""
    if val is None:
        return "None"
    t = type(val).__name__
    if hasattr(val, "dtype"):
        return f"{t}[{val.dtype}]"
    return t


def safe_repr(val: Any, max_len: int = 100) -> str:
    """Get a safe truncated repr of a value."""
    if val is None:
        return "None"
    if isinstance(val, bytes):
        return f"<bytes len={len(val)}>"
    if isinstance(val, dict):
        if "bytes" in val:
            return f"<dict with 'bytes' key, len={len(val.get('bytes', b''))}>"
        return f"<dict keys={list(val.keys())}>"
    r = repr(val)
    if len(r) > max_len:
        return r[: max_len - 3] + "..."
    return r


def main() -> int:
    """Main discovery workflow."""
    print("=" * 70)
    print("ISLES24-MR-Lite Dataset Discovery")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)
    print()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Import datasets library
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: 'datasets' library not installed.")
        print("Run: uv add datasets")
        return 1

    # =========================================================================
    # PHASE 1: Load Dataset (Full Download)
    # =========================================================================
    print(f"[1/4] Loading dataset: {DATASET_ID}")
    print("      This will download the FULL dataset...")
    print()

    try:
        # Try loading without streaming first to get full access
        ds = load_dataset(DATASET_ID)
        print("      SUCCESS: Dataset loaded")
        print(f"      Splits available: {list(ds.keys())}")
        print()
    except Exception as e:
        print(f"      ERROR loading dataset: {e}")
        print()
        print("      Trying streaming mode as fallback...")
        try:
            ds = load_dataset(DATASET_ID, streaming=True)
            print("      SUCCESS (streaming): Dataset loaded")
            print(f"      Splits available: {list(ds.keys())}")
        except Exception as e2:
            print(f"      FATAL: Cannot load dataset: {e2}")
            return 1

    # =========================================================================
    # PHASE 2: Inspect Schema (Features)
    # =========================================================================
    print("[2/4] Inspecting schema...")
    print()

    report_lines: list[str] = []
    report_lines.append("=" * 70)
    report_lines.append("ISLES24-MR-Lite Schema Discovery Report")
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append(f"Dataset: {DATASET_ID}")
    report_lines.append("=" * 70)
    report_lines.append("")

    for split_name in ds:
        split = ds[split_name]
        report_lines.append(f"SPLIT: {split_name}")
        report_lines.append("-" * 50)

        # Get features/schema
        if hasattr(split, "features"):
            features = split.features
            report_lines.append(
                f"Number of rows: {len(split) if hasattr(split, '__len__') else 'unknown (streaming)'}"
            )
            report_lines.append("")
            report_lines.append("FEATURES (columns):")
            for feat_name, feat_type in features.items():
                report_lines.append(f"  - {feat_name}: {feat_type}")
            report_lines.append("")
        else:
            report_lines.append("  (No features metadata available)")
            report_lines.append("")

    print("      Schema extracted.")
    print()

    # =========================================================================
    # PHASE 3: Sample Inspection (check actual data)
    # =========================================================================
    print("[3/4] Inspecting sample rows...")
    print()

    # Use the first available split (usually 'train')
    main_split_name = next(iter(ds.keys()))
    main_split = ds[main_split_name]

    report_lines.append("=" * 70)
    report_lines.append("SAMPLE DATA INSPECTION")
    report_lines.append("=" * 70)
    report_lines.append("")

    # Check first 3 rows in detail
    report_lines.append("First 3 rows (detailed):")
    report_lines.append("-" * 50)

    sample_count = 0
    column_value_types: dict[str, Counter[str]] = {}

    # Iterate through dataset
    iterable = iter(main_split) if hasattr(main_split, "__iter__") else main_split

    for i, row in enumerate(iterable):
        if i < 3:
            report_lines.append(f"\nROW {i}:")
            for key, val in row.items():
                val_type = safe_type_name(val)
                val_repr = safe_repr(val)
                report_lines.append(f"  {key}:")
                report_lines.append(f"    type: {val_type}")
                report_lines.append(f"    value: {val_repr}")

        # Track types for all rows
        for key, val in row.items():
            if key not in column_value_types:
                column_value_types[key] = Counter()
            column_value_types[key][safe_type_name(val)] += 1

        sample_count += 1

        # Progress indicator
        if sample_count % 50 == 0:
            print(f"      Processed {sample_count} rows...")

    print(f"      Total rows processed: {sample_count}")
    print()

    # =========================================================================
    # PHASE 4: Consistency Check
    # =========================================================================
    print("[4/4] Checking consistency across all rows...")
    print()

    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("CONSISTENCY ANALYSIS (all rows)")
    report_lines.append("=" * 70)
    report_lines.append("")
    report_lines.append(f"Total rows analyzed: {sample_count}")
    report_lines.append("")

    report_lines.append("Column type distribution:")
    report_lines.append("-" * 50)
    for col_name, type_counts in column_value_types.items():
        report_lines.append(f"\n  {col_name}:")
        for type_name, count in type_counts.most_common():
            pct = (count / sample_count) * 100
            report_lines.append(f"    {type_name}: {count} ({pct:.1f}%)")

    # =========================================================================
    # PHASE 5: CaseAdapter Compatibility Check
    # =========================================================================
    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("CASEADAPTER COMPATIBILITY CHECK")
    report_lines.append("=" * 70)
    report_lines.append("")

    expected_columns = ["dwi", "adc", "flair", "mask", "ground_truth", "participant_id"]
    actual_columns = list(column_value_types.keys())

    report_lines.append("Expected by CaseAdapter:")
    for col in expected_columns:
        status = "FOUND" if col in actual_columns else "MISSING"
        report_lines.append(f"  {col}: {status}")

    report_lines.append("")
    report_lines.append("Actual columns in dataset:")
    for col in actual_columns:
        expected = "expected" if col in expected_columns else "UNEXPECTED"
        report_lines.append(f"  {col}: {expected}")

    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("END OF REPORT")
    report_lines.append("=" * 70)

    # Write report
    report_content = "\n".join(report_lines)
    REPORT_FILE.write_text(report_content)

    print(f"Report written to: {REPORT_FILE}")
    print()
    print("=" * 70)
    print("DISCOVERY COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print(f"  1. Review: {REPORT_FILE}")
    print("  2. Compare findings against src/stroke_deepisles_demo/data/adapter.py")
    print("  3. Update adapter if schema differs from expectations")
    print()

    # Print summary to stdout as well
    print("-" * 70)
    print("QUICK SUMMARY:")
    print("-" * 70)
    print(f"Columns found: {actual_columns}")
    print()
    missing = [c for c in expected_columns if c not in actual_columns]
    if missing:
        print(f"WARNING: Expected columns MISSING: {missing}")
    unexpected = [c for c in actual_columns if c not in expected_columns]
    if unexpected:
        print(f"NOTE: Unexpected columns found: {unexpected}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
