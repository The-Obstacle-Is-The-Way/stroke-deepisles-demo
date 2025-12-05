"""Integration tests with real ISLES24 data."""

from __future__ import annotations

from pathlib import Path

import pytest

from stroke_deepisles_demo.data.loader import load_isles_dataset

REAL_DATA_PATH = Path("data/scratch/isles24_extracted")


@pytest.mark.skipif(not REAL_DATA_PATH.exists(), reason="Real data not found in data/scratch")
def test_load_real_data_count() -> None:
    """Verify that we can load the expected number of cases from real data."""
    dataset = load_isles_dataset(source=REAL_DATA_PATH)

    # We expect 149 cases based on schema report
    assert len(dataset) == 149

    # Check a specific known case
    case = dataset.get_case("sub-stroke0005")
    assert case["dwi"].name == "sub-stroke0005_ses-02_dwi.nii.gz"
    assert case["dwi"].exists()
    assert case["adc"].exists()
    assert case["ground_truth"] is not None
    assert case["ground_truth"].exists()


@pytest.mark.skipif(not REAL_DATA_PATH.exists(), reason="Real data not found in data/scratch")
def test_real_data_subject_ids() -> None:
    """Verify subject ID formatting on real data."""
    dataset = load_isles_dataset(source=REAL_DATA_PATH)
    ids = dataset.list_case_ids()

    assert len(ids) == 149
    assert ids[0] == "sub-stroke0001"
    # We know there are gaps, so just check the format
    for subject_id in ids:
        assert subject_id.startswith("sub-stroke")
        assert len(subject_id) == len("sub-strokeXXXX")
