"""Unit tests for HuggingFace dataset adapter with mocked HF dataset."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.exceptions import DataLoadError
from stroke_deepisles_demo.data.adapter import HuggingFaceDataset, build_huggingface_dataset


def create_mock_hf_example(subject_id: str, include_mask: bool = True) -> dict[str, Any]:
    """Create a mock HuggingFace dataset example."""
    example: dict[str, Any] = {
        "subject_id": subject_id,
        "dwi": {"bytes": b"fake_dwi_nifti_data", "path": f"{subject_id}_dwi.nii.gz"},
        "adc": {"bytes": b"fake_adc_nifti_data", "path": f"{subject_id}_adc.nii.gz"},
    }
    if include_mask:
        example["lesion_mask"] = {
            "bytes": b"fake_mask_nifti_data",
            "path": f"{subject_id}_lesion-msk.nii.gz",
        }
    else:
        example["lesion_mask"] = None
    return example


@pytest.fixture
def mock_hf_dataset() -> MagicMock:
    """Create a mock HuggingFace dataset with 3 subjects."""
    examples = [
        create_mock_hf_example("sub-stroke0001"),
        create_mock_hf_example("sub-stroke0002"),
        create_mock_hf_example("sub-stroke0003", include_mask=False),
    ]

    mock_ds = MagicMock()
    mock_ds.__len__ = MagicMock(return_value=len(examples))
    mock_ds.__iter__ = MagicMock(return_value=iter(examples))
    mock_ds.__getitem__ = MagicMock(side_effect=lambda i: examples[i])

    return mock_ds


class TestHuggingFaceDataset:
    """Tests for HuggingFaceDataset class."""

    def test_get_case_writes_files_to_temp_dir(self, mock_hf_dataset: MagicMock) -> None:
        """Test that get_case writes NIfTI bytes to temp files."""
        case_ids = ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _hf_dataset=mock_hf_dataset,
            _case_ids=case_ids,
        )

        try:
            case = ds.get_case(0)

            assert "dwi" in case
            assert "adc" in case
            assert case["dwi"].exists()
            assert case["adc"].exists()
            assert case["dwi"].read_bytes() == b"fake_dwi_nifti_data"
            assert case["adc"].read_bytes() == b"fake_adc_nifti_data"
        finally:
            ds.cleanup()

    def test_get_case_includes_ground_truth_when_available(
        self, mock_hf_dataset: MagicMock
    ) -> None:
        """Test that ground truth is included when lesion_mask is present."""
        case_ids = ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _hf_dataset=mock_hf_dataset,
            _case_ids=case_ids,
        )

        try:
            case = ds.get_case(0)  # Has mask
            assert "ground_truth" in case
            assert case["ground_truth"].read_bytes() == b"fake_mask_nifti_data"

            case_no_mask = ds.get_case(2)  # No mask
            assert "ground_truth" not in case_no_mask
        finally:
            ds.cleanup()

    def test_get_case_caches_results(self, mock_hf_dataset: MagicMock) -> None:
        """Test that get_case returns cached paths on subsequent calls."""
        case_ids = ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _hf_dataset=mock_hf_dataset,
            _case_ids=case_ids,
        )

        try:
            case1 = ds.get_case(0)
            case2 = ds.get_case(0)

            # Same object returned (cached)
            assert case1 is case2

            # Dataset was only accessed once
            assert mock_hf_dataset.__getitem__.call_count == 1
        finally:
            ds.cleanup()

    def test_context_manager_cleans_up_temp_files(self, mock_hf_dataset: MagicMock) -> None:
        """Test that using context manager cleans up temp files."""
        case_ids = ["sub-stroke0001"]
        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _hf_dataset=mock_hf_dataset,
            _case_ids=case_ids,
        )

        with ds:
            case = ds.get_case(0)
            temp_dir = case["dwi"].parent.parent
            assert temp_dir.exists()

        # After context exit, temp dir should be gone
        assert not temp_dir.exists()

    def test_cleanup_clears_cache(self, mock_hf_dataset: MagicMock) -> None:
        """Test that cleanup clears the case cache."""
        case_ids = ["sub-stroke0001"]
        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _hf_dataset=mock_hf_dataset,
            _case_ids=case_ids,
        )

        ds.get_case(0)
        assert len(ds._cached_cases) == 1

        ds.cleanup()
        assert len(ds._cached_cases) == 0

    def test_get_case_raises_data_load_error_on_malformed_data(self) -> None:
        """Test that get_case raises DataLoadError for malformed HF data."""
        # Create mock with missing 'bytes' key
        malformed_example = {"subject_id": "sub-stroke0001", "dwi": {}, "adc": {}}
        mock_ds = MagicMock()
        mock_ds.__len__ = MagicMock(return_value=1)
        mock_ds.__getitem__ = MagicMock(return_value=malformed_example)

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _hf_dataset=mock_ds,
            _case_ids=["sub-stroke0001"],
        )

        try:
            with pytest.raises(DataLoadError, match="Malformed HuggingFace data"):
                ds.get_case(0)
        finally:
            ds.cleanup()


class TestBuildHuggingFaceDataset:
    """Tests for build_huggingface_dataset function."""

    @patch("datasets.load_dataset")
    def test_loads_dataset_from_hub(self, mock_load_dataset: MagicMock) -> None:
        """Test that build_huggingface_dataset uses streaming to enumerate case IDs."""
        mock_streaming_ds = MagicMock()
        mock_streaming_ds.__iter__ = MagicMock(
            return_value=iter([{"subject_id": "sub-stroke0001"}])
        )
        mock_load_dataset.return_value = mock_streaming_ds

        result = build_huggingface_dataset("test/my-dataset")

        # Should use streaming mode for initial case ID enumeration
        mock_load_dataset.assert_called_once_with("test/my-dataset", split="train", streaming=True)
        assert isinstance(result, HuggingFaceDataset)
        assert result.dataset_id == "test/my-dataset"
        assert result._case_ids == ["sub-stroke0001"]
        # Dataset should be None initially (lazy load)
        assert result._hf_dataset is None
