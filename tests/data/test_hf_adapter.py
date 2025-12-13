"""Unit tests for HuggingFace dataset wrapper."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from stroke_deepisles_demo.data.loader import HuggingFaceDatasetWrapper


class TestHuggingFaceDatasetWrapper:
    """Tests for HuggingFaceDatasetWrapper class."""

    @pytest.fixture
    def mock_hf_dataset(self) -> MagicMock:
        """Create a mock HuggingFace dataset."""
        dataset = MagicMock()

        # Mock dataset length
        dataset.__len__.return_value = 3

        # Mock column access for fast index building
        # This simulates dataset["subject_id"]
        dataset.__getitem__.side_effect = lambda key: (
            ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
            if key == "subject_id"
            else MagicMock()
        )

        return dataset

    def test_init_builds_index_correctly(self, mock_hf_dataset: MagicMock) -> None:
        """Test that initialization builds the subject ID index."""
        wrapper = HuggingFaceDatasetWrapper(mock_hf_dataset, "test/dataset")

        assert len(wrapper) == 3
        assert wrapper.list_case_ids() == ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
        assert wrapper._case_id_to_index["sub-stroke0001"] == 0
        assert wrapper._case_id_to_index["sub-stroke0003"] == 2

    def test_get_case_materializes_files(self, mock_hf_dataset: MagicMock) -> None:
        """Test that get_case materializes NIfTI objects to files."""
        # Setup row return for get_case
        mock_dwi = MagicMock()
        mock_adc = MagicMock()
        mock_mask = MagicMock()

        row_data = {
            "subject_id": "sub-stroke0001",
            "dwi": mock_dwi,
            "adc": mock_adc,
            "lesion_mask": mock_mask,
        }

        # Reset side_effect to return row for integer index
        mock_hf_dataset.__getitem__.side_effect = (
            lambda idx: row_data if isinstance(idx, int) else ["sub-stroke0001"]
        )

        wrapper = HuggingFaceDatasetWrapper(mock_hf_dataset, "test/dataset")

        with wrapper:
            case = wrapper.get_case("sub-stroke0001")

            # Verify file paths
            assert case["dwi"].name == "sub-stroke0001_dwi.nii.gz"
            assert case["adc"].name == "sub-stroke0001_adc.nii.gz"
            assert case["ground_truth"].name == "sub-stroke0001_lesion-msk.nii.gz"

            # Verify to_filename called
            mock_dwi.to_filename.assert_called_once()
            mock_adc.to_filename.assert_called_once()
            mock_mask.to_filename.assert_called_once()

            # Verify temporary directory usage
            assert wrapper._temp_dir is not None
            assert case["dwi"].parent == wrapper._temp_dir / "sub-stroke0001"

    def test_get_case_handles_missing_mask(self, mock_hf_dataset: MagicMock) -> None:
        """Test that get_case handles cases without lesion mask."""
        row_data = {
            "subject_id": "sub-stroke0002",
            "dwi": MagicMock(),
            "adc": MagicMock(),
            "lesion_mask": None,
        }

        mock_hf_dataset.__getitem__.side_effect = (
            lambda idx: row_data if isinstance(idx, int) else ["sub-stroke0002"]
        )

        wrapper = HuggingFaceDatasetWrapper(mock_hf_dataset, "test/dataset")

        with wrapper:
            case = wrapper.get_case("sub-stroke0002")

            assert "dwi" in case
            assert "adc" in case
            assert "ground_truth" not in case

    def test_cleanup_removes_temp_dir(self, mock_hf_dataset: MagicMock) -> None:
        """Test that cleanup removes the temporary directory."""
        row_data = {
            "subject_id": "sub-stroke0001",
            "dwi": MagicMock(),
            "adc": MagicMock(),
            "lesion_mask": None,
        }
        mock_hf_dataset.__getitem__.side_effect = (
            lambda idx: row_data if isinstance(idx, int) else ["sub-stroke0001"]
        )

        wrapper = HuggingFaceDatasetWrapper(mock_hf_dataset, "test/dataset")

        # Create temp dir by accessing a case
        wrapper.get_case(0)
        temp_dir = wrapper._temp_dir

        assert temp_dir is not None
        assert temp_dir.exists()

        # cleanup
        wrapper.cleanup()

        assert not temp_dir.exists()
        assert wrapper._temp_dir is None

    def test_fallback_iteration(self) -> None:
        """Test fallback to iteration if column access fails."""
        dataset = MagicMock()
        dataset.__len__.return_value = 2

        # Configure iteration for fallback
        dataset.__iter__.return_value = iter([{"subject_id": "sub-0"}, {"subject_id": "sub-1"}])

        # Fail column access
        def getitem(key: Any) -> Any:
            if key == "subject_id":
                raise ValueError("No column access")
            if isinstance(key, int):
                return {"subject_id": f"sub-{key}"}
            return MagicMock()

        dataset.__getitem__.side_effect = getitem

        wrapper = HuggingFaceDatasetWrapper(dataset, "test/dataset")

        assert wrapper._case_id_to_index["sub-0"] == 0
        assert wrapper._case_id_to_index["sub-1"] == 1
