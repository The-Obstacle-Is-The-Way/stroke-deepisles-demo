"""Tests for case adapter module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from stroke_deepisles_demo.data.adapter import CaseAdapter

if TYPE_CHECKING:
    from unittest.mock import MagicMock


class TestCaseAdapter:
    """Tests for CaseAdapter."""

    def test_list_case_ids_returns_strings(self, mock_hf_dataset: MagicMock) -> None:
        """list_case_ids returns list of string identifiers."""
        adapter = CaseAdapter(mock_hf_dataset)
        case_ids = adapter.list_case_ids()

        assert isinstance(case_ids, list)
        assert all(isinstance(cid, str) for cid in case_ids)
        assert case_ids == ["sub-001"]

    def test_len_matches_dataset_size(self, mock_hf_dataset: MagicMock) -> None:
        """len(adapter) equals number of cases in dataset."""
        adapter = CaseAdapter(mock_hf_dataset)

        assert len(adapter) == len(mock_hf_dataset)

    def test_get_case_by_string_id(self, mock_hf_dataset: MagicMock) -> None:
        """Can retrieve case by string identifier."""
        adapter = CaseAdapter(mock_hf_dataset)
        case_ids = adapter.list_case_ids()

        case = adapter.get_case(case_ids[0])

        assert isinstance(case, dict)
        assert "dwi" in case
        assert "adc" in case
        # Paths should be Path objects or convertible
        from pathlib import Path

        assert isinstance(case["dwi"], (Path, str))

    def test_get_case_by_index(self, mock_hf_dataset: MagicMock) -> None:
        """Can retrieve case by integer index."""
        adapter = CaseAdapter(mock_hf_dataset)

        case_id, case = adapter.get_case_by_index(0)

        assert isinstance(case_id, str)
        assert case["dwi"] is not None

    def test_get_case_invalid_id_raises(self, mock_hf_dataset: MagicMock) -> None:
        """Raises KeyError for invalid case ID."""
        adapter = CaseAdapter(mock_hf_dataset)

        with pytest.raises(KeyError):
            adapter.get_case("nonexistent-case-id")

    def test_iteration(self, mock_hf_dataset: MagicMock) -> None:
        """Can iterate over case IDs."""
        adapter = CaseAdapter(mock_hf_dataset)

        case_ids = list(adapter)

        assert len(case_ids) == len(adapter)
