"""Tests for the data adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from stroke_deepisles_demo.data.adapter import (
    LocalDataset,
    build_local_dataset,
    parse_subject_id,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_parse_subject_id_extracts_correctly() -> None:
    """Test extracting subject ID from BIDS filename."""
    # Valid cases
    assert parse_subject_id("sub-stroke0005_ses-02_dwi.nii.gz") == "sub-stroke0005"
    assert parse_subject_id("sub-stroke0149_ses-02_adc.nii.gz") == "sub-stroke0149"
    assert parse_subject_id("sub-stroke1234_ses-02_lesion-msk.nii.gz") == "sub-stroke1234"

    # Invalid cases
    assert parse_subject_id("random_file.nii.gz") is None
    assert parse_subject_id("sub-strokeABC_ses-02_dwi.nii.gz") is None  # Non-digit ID


def test_build_local_dataset_matches_files(synthetic_isles_dir: Path) -> None:
    """Test that files are correctly matched by subject ID."""
    dataset = build_local_dataset(synthetic_isles_dir)

    assert isinstance(dataset, LocalDataset)
    assert len(dataset) == 2  # synthetic_isles_dir creates 2 subjects
    assert dataset.list_case_ids() == ["sub-stroke0001", "sub-stroke0002"]

    # Verify matching logic
    case1 = dataset.get_case("sub-stroke0001")
    assert case1["dwi"].name == "sub-stroke0001_ses-02_dwi.nii.gz"
    assert case1["adc"].name == "sub-stroke0001_ses-02_adc.nii.gz"
    assert case1["ground_truth"] is not None
    assert case1["ground_truth"].name == "sub-stroke0001_ses-02_lesion-msk.nii.gz"


def test_get_case_returns_case_files(synthetic_isles_dir: Path) -> None:
    """Test retrieval of cases by ID and index."""
    dataset = build_local_dataset(synthetic_isles_dir)

    # By ID
    case_by_id = dataset.get_case("sub-stroke0001")
    assert isinstance(case_by_id, dict)
    assert "dwi" in case_by_id
    assert "adc" in case_by_id

    # By Index
    case_by_idx = dataset.get_case(0)
    assert isinstance(case_by_idx, dict)
    assert case_by_id == case_by_idx  # Should be the same case


def test_build_local_dataset_skips_incomplete(
    synthetic_isles_dir: Path,
) -> None:
    """Test that incomplete cases (missing ADC) are skipped."""
    # Delete ADC for subject 2
    adc_file = synthetic_isles_dir / "Images-ADC" / "sub-stroke0002_ses-02_adc.nii.gz"
    adc_file.unlink()

    dataset = build_local_dataset(synthetic_isles_dir)

    # Subject 2 should be gone
    assert len(dataset) == 1
    assert dataset.list_case_ids() == ["sub-stroke0001"]


def test_build_local_dataset_handles_missing_mask(
    synthetic_isles_dir: Path,
) -> None:
    """Test that missing mask results in ground_truth=None (if allowed)."""
    # NOTE: Adapter currently allows missing mask?
    # Spec says: "ground_truth=mask_file if mask_file.exists() else None"
    # So yes, it should load but with None.

    # Delete Mask for subject 2
    mask_file = synthetic_isles_dir / "Masks" / "sub-stroke0002_ses-02_lesion-msk.nii.gz"
    mask_file.unlink()

    dataset = build_local_dataset(synthetic_isles_dir)

    # Subject 2 should still exist
    assert len(dataset) == 2

    case2 = dataset.get_case("sub-stroke0002")
    assert case2.get("ground_truth") is None
