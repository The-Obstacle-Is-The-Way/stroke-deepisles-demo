"""Tests for the data loader."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from stroke_deepisles_demo.data.adapter import LocalDataset
from stroke_deepisles_demo.data.loader import load_isles_dataset

if TYPE_CHECKING:
    from pathlib import Path


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


def test_load_raises_not_implemented_for_hf() -> None:
    """Test that HF mode raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        load_isles_dataset(source="fake/dataset", local_mode=False)
