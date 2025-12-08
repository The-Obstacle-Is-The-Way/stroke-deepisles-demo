"""Tests for the data loader."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from stroke_deepisles_demo.data.adapter import HuggingFaceDataset, LocalDataset, logger
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


def test_load_hf_warns_on_non_standard_dataset() -> None:
    """Test that loading a non-standard HF dataset logs a warning.

    Note: With pre-computed case IDs, the dataset ID mismatch is only detected
    at build time (warning logged), not at get_case() time. The actual 404 error
    would only occur when trying to download a case that doesn't exist.
    """
    with patch.object(logger, "warning") as mock_warning:
        ds = load_isles_dataset(source="fake/nonexistent-dataset", local_mode=False)
        mock_warning.assert_called_once()
        assert "does not match pre-computed constants" in mock_warning.call_args[0][0]
        # Dataset is still created with pre-computed case IDs
        assert isinstance(ds, HuggingFaceDataset)
        assert len(ds) == 149  # Uses pre-computed list


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
