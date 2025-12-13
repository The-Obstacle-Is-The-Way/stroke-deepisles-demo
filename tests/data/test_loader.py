"""Tests for the data loader."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.data.adapter import LocalDataset
from stroke_deepisles_demo.data.loader import HuggingFaceDatasetWrapper, load_isles_dataset

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


def test_load_hf_calls_load_dataset() -> None:
    """Test that loading from HF calls datasets.load_dataset."""
    with patch("datasets.load_dataset") as mock_load:
        mock_ds = MagicMock()
        mock_ds.__len__.return_value = 0
        # Mock column access for index building
        mock_ds.__getitem__.side_effect = lambda key: [] if key == "subject_id" else MagicMock()
        mock_load.return_value = mock_ds

        ds = load_isles_dataset(source="my/dataset", local_mode=False)

        assert isinstance(ds, HuggingFaceDatasetWrapper)
        mock_load.assert_called_once()
        assert mock_load.call_args[0][0] == "my/dataset"


@pytest.mark.integration
@SKIP_IN_CI
def test_load_from_huggingface_returns_hf_dataset() -> None:
    """Test that loading from HuggingFace returns a HuggingFaceDatasetWrapper.

    Note: Skipped in CI due to large download size (~GB) and limited disk space.
    Run locally with: pytest -m integration tests/data/test_loader.py
    """
    with load_isles_dataset() as dataset:  # Default is HuggingFace mode
        assert isinstance(dataset, HuggingFaceDatasetWrapper)
        # We can't guarantee length if we don't mock, but we can check type
        # Real test might fail if network issue or auth issue
