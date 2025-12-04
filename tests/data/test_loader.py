"""Tests for data loader module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.exceptions import DataLoadError
from stroke_deepisles_demo.data.loader import (
    DatasetInfo,
    get_dataset_info,
    load_isles_dataset,
)


class TestLoadIslesDataset:
    """Tests for load_isles_dataset."""

    def test_calls_hf_load_dataset(self) -> None:
        """Calls datasets.load_dataset with correct arguments."""
        with patch("stroke_deepisles_demo.data.loader.load_dataset") as mock_load:
            mock_load.return_value = MagicMock()

            load_isles_dataset("test/dataset")

            mock_load.assert_called_once()
            call_args = mock_load.call_args
            assert call_args.args[0] == "test/dataset"

    def test_returns_dataset_object(self) -> None:
        """Returns the loaded Dataset object."""
        with patch("stroke_deepisles_demo.data.loader.load_dataset") as mock_load:
            expected = MagicMock()
            mock_load.return_value = expected

            result = load_isles_dataset()

            assert result is expected

    def test_handles_load_error(self) -> None:
        """Wraps HF errors in DataLoadError."""
        with patch("stroke_deepisles_demo.data.loader.load_dataset") as mock_load:
            mock_load.side_effect = Exception("Network error")

            with pytest.raises(DataLoadError, match="Network error"):
                load_isles_dataset()


class TestGetDatasetInfo:
    """Tests for get_dataset_info."""

    def test_returns_datasetinfo(self) -> None:
        """Returns DatasetInfo with expected fields."""
        with patch("stroke_deepisles_demo.data.loader.load_dataset") as mock_load:
            mock_ds = MagicMock()
            mock_ds.__len__ = MagicMock(return_value=149)
            # Mock info.splits['train'].num_examples
            mock_ds.info.splits.__getitem__.return_value.num_examples = 149
            # Mock features as dict-like
            mock_ds.features = {"dwi": None, "adc": None, "mask": None}
            mock_load.return_value = mock_ds

            info = get_dataset_info()

            assert isinstance(info, DatasetInfo)
            assert info.num_cases == 149
            assert "dwi" in info.modalities
            assert info.has_ground_truth is True


@pytest.mark.integration
class TestLoadIslesDatasetIntegration:
    """Integration tests that hit the real HuggingFace Hub."""

    @pytest.mark.slow
    def test_load_real_dataset(self) -> None:
        """Actually loads ISLES24-MR-Lite from HF Hub."""
        # This test requires network access
        # Run with: pytest -m integration
        # Using streaming=True to avoid downloading everything
        try:
            dataset = load_isles_dataset(streaming=True)
            assert dataset is not None
            # Verify we got metadata/features - this confirms connectivity
            # Iterating might trigger heavy downloads or fail if dataset is empty/gated
            assert hasattr(dataset, "features")
            assert len(dataset.features) > 0
        except Exception as e:
            pytest.fail(f"Failed to load real dataset: {e}")
