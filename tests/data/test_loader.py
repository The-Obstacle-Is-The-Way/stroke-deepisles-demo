"""Tests for the data loader."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from datasets.exceptions import DatasetNotFoundError

from stroke_deepisles_demo.data.adapter import HuggingFaceDataset, LocalDataset
from stroke_deepisles_demo.data.loader import load_isles_dataset

if TYPE_CHECKING:
    from pathlib import Path

# Skip tests that download large datasets in CI (limited disk space)
SKIP_IN_CI = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Skips large HuggingFace downloads in CI (disk space)",
)


def test_load_from_local_returns_local_dataset(synthetic_isles_dir: Path) -> None:
    """Test that loading from local path returns a LocalDataset."""
    dataset = load_isles_dataset(source=synthetic_isles_dir, local_mode=True)
    assert isinstance(dataset, LocalDataset)
    assert len(dataset) > 0


def test_load_from_local_finds_all_cases(synthetic_isles_dir: Path) -> None:
    """Test that the loader correctly delegates finding cases to adapter."""
    dataset = load_isles_dataset(source=synthetic_isles_dir)
    assert len(dataset) == 2
    assert dataset.list_case_ids() == ["sub-stroke0001", "sub-stroke0002"]


def test_load_hf_raises_on_invalid_dataset() -> None:
    """Test that loading a non-existent HF dataset raises DatasetNotFoundError."""
    with pytest.raises(DatasetNotFoundError):
        load_isles_dataset(source="fake/nonexistent-dataset", local_mode=False)


@pytest.mark.integration
@SKIP_IN_CI
def test_load_from_huggingface_returns_hf_dataset() -> None:
    """Test that loading from HuggingFace returns a HuggingFaceDataset.

    Note: Skipped in CI due to large download size (~GB) and limited disk space.
    Run locally with: pytest -m integration tests/data/test_loader.py
    """
    with load_isles_dataset() as dataset:  # Default is HuggingFace mode
        assert isinstance(dataset, HuggingFaceDataset)
        assert len(dataset) == 149
        assert dataset.list_case_ids()[0] == "sub-stroke0001"
