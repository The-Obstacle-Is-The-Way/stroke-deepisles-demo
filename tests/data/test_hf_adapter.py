"""Unit tests for HuggingFace dataset adapter with mocked HF data access."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.exceptions import DataLoadError
from stroke_deepisles_demo.data.adapter import HuggingFaceDataset, build_huggingface_dataset


def create_mock_parquet_data(subject_id: str, include_mask: bool = True) -> dict[str, Any]:
    """Create mock data that matches what we read from parquet files."""
    data: dict[str, Any] = {
        "subject_id": subject_id,
        "dwi": {"bytes": b"fake_dwi_nifti_data", "path": f"{subject_id}_dwi.nii.gz"},
        "adc": {"bytes": b"fake_adc_nifti_data", "path": f"{subject_id}_adc.nii.gz"},
    }
    if include_mask:
        data["lesion_mask"] = {
            "bytes": b"fake_mask_nifti_data",
            "path": f"{subject_id}_lesion-msk.nii.gz",
        }
    else:
        data["lesion_mask"] = None
    return data


class TestHuggingFaceDataset:
    """Tests for HuggingFaceDataset class."""

    def test_get_case_writes_files_to_temp_dir(self) -> None:
        """Test that get_case writes NIfTI bytes to temp files."""
        case_ids = ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
        case_index = {cid: idx for idx, cid in enumerate(case_ids)}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        # Mock the download method
        mock_data = {
            "dwi_bytes": b"fake_dwi_nifti_data",
            "adc_bytes": b"fake_adc_nifti_data",
            "mask_bytes": b"fake_mask_nifti_data",
        }

        try:
            with patch.object(ds, "_download_case_from_parquet", return_value=mock_data):
                case = ds.get_case(0)

                assert "dwi" in case
                assert "adc" in case
                assert case["dwi"].exists()
                assert case["adc"].exists()
                assert case["dwi"].read_bytes() == b"fake_dwi_nifti_data"
                assert case["adc"].read_bytes() == b"fake_adc_nifti_data"
        finally:
            ds.cleanup()

    def test_get_case_includes_ground_truth_when_available(self) -> None:
        """Test that ground truth is included when lesion_mask is present."""
        case_ids = ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
        case_index = {cid: idx for idx, cid in enumerate(case_ids)}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        try:
            # Case with mask
            mock_data_with_mask = {
                "dwi_bytes": b"fake_dwi_nifti_data",
                "adc_bytes": b"fake_adc_nifti_data",
                "mask_bytes": b"fake_mask_nifti_data",
            }
            with patch.object(ds, "_download_case_from_parquet", return_value=mock_data_with_mask):
                case = ds.get_case(0)
                assert "ground_truth" in case
                assert case["ground_truth"].read_bytes() == b"fake_mask_nifti_data"

            # Case without mask
            mock_data_no_mask = {
                "dwi_bytes": b"fake_dwi_nifti_data",
                "adc_bytes": b"fake_adc_nifti_data",
            }
            with patch.object(ds, "_download_case_from_parquet", return_value=mock_data_no_mask):
                case_no_mask = ds.get_case(2)
                assert "ground_truth" not in case_no_mask
        finally:
            ds.cleanup()

    def test_get_case_caches_results(self) -> None:
        """Test that get_case returns cached paths on subsequent calls."""
        case_ids = ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
        case_index = {cid: idx for idx, cid in enumerate(case_ids)}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        mock_data = {
            "dwi_bytes": b"fake_dwi_nifti_data",
            "adc_bytes": b"fake_adc_nifti_data",
        }

        try:
            with patch.object(
                ds, "_download_case_from_parquet", return_value=mock_data
            ) as mock_download:
                case1 = ds.get_case(0)
                case2 = ds.get_case(0)

                # Same object returned (cached)
                assert case1 is case2

                # Download was only called once
                assert mock_download.call_count == 1
        finally:
            ds.cleanup()

    def test_context_manager_cleans_up_temp_files(self) -> None:
        """Test that using context manager cleans up temp files."""
        case_ids = ["sub-stroke0001"]
        case_index = {"sub-stroke0001": 0}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        mock_data = {
            "dwi_bytes": b"fake_dwi_nifti_data",
            "adc_bytes": b"fake_adc_nifti_data",
        }

        with patch.object(ds, "_download_case_from_parquet", return_value=mock_data), ds:
            case = ds.get_case(0)
            temp_dir = case["dwi"].parent.parent
            assert temp_dir.exists()

        # After context exit, temp dir should be gone
        assert not temp_dir.exists()

    def test_cleanup_clears_cache(self) -> None:
        """Test that cleanup clears the case cache."""
        case_ids = ["sub-stroke0001"]
        case_index = {"sub-stroke0001": 0}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        mock_data = {
            "dwi_bytes": b"fake_dwi_nifti_data",
            "adc_bytes": b"fake_adc_nifti_data",
        }

        with patch.object(ds, "_download_case_from_parquet", return_value=mock_data):
            ds.get_case(0)
            assert len(ds._cached_cases) == 1

        ds.cleanup()
        assert len(ds._cached_cases) == 0

    def test_get_case_by_string_id(self) -> None:
        """Test that get_case works with string case IDs."""
        case_ids = ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"]
        case_index = {cid: idx for idx, cid in enumerate(case_ids)}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        mock_data = {
            "dwi_bytes": b"fake_dwi_nifti_data",
            "adc_bytes": b"fake_adc_nifti_data",
        }

        try:
            with patch.object(
                ds, "_download_case_from_parquet", return_value=mock_data
            ) as mock_download:
                case = ds.get_case("sub-stroke0002")
                assert case["dwi"].exists()
                # Should have been called with index 1 (second case)
                mock_download.assert_called_once_with(1, "sub-stroke0002")
        finally:
            ds.cleanup()

    def test_get_case_raises_key_error_for_invalid_id(self) -> None:
        """Test that get_case raises KeyError for invalid case ID."""
        case_ids = ["sub-stroke0001"]
        case_index = {"sub-stroke0001": 0}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        with pytest.raises(KeyError, match="not found in dataset"):
            ds.get_case("sub-stroke9999")

    def test_get_case_raises_index_error_for_out_of_range(self) -> None:
        """Test that get_case raises IndexError for out of range index."""
        case_ids = ["sub-stroke0001"]
        case_index = {"sub-stroke0001": 0}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        with pytest.raises(IndexError, match="out of range"):
            ds.get_case(99)


class TestBuildHuggingFaceDataset:
    """Tests for build_huggingface_dataset function."""

    def test_uses_precomputed_case_ids(self) -> None:
        """Test that build_huggingface_dataset uses pre-computed case IDs."""
        result = build_huggingface_dataset("hugging-science/isles24-stroke")

        assert isinstance(result, HuggingFaceDataset)
        assert result.dataset_id == "hugging-science/isles24-stroke"
        # Should have 149 cases from pre-computed list
        assert len(result._case_ids) == 149
        assert "sub-stroke0001" in result._case_ids
        assert "sub-stroke0189" in result._case_ids

    def test_case_index_mapping_is_correct(self) -> None:
        """Test that case index mapping matches case IDs order."""
        result = build_huggingface_dataset("hugging-science/isles24-stroke")

        # First case should map to index 0
        assert result._case_index["sub-stroke0001"] == 0
        # Last case should map to index 148
        assert result._case_index["sub-stroke0189"] == 148

    def test_warns_for_different_dataset_id(self) -> None:
        """Test that a warning is logged for non-standard dataset IDs."""
        from stroke_deepisles_demo.data.adapter import logger

        with patch.object(logger, "warning") as mock_warning:
            build_huggingface_dataset("some-other/dataset")
            mock_warning.assert_called_once()
            assert "does not match pre-computed constants" in mock_warning.call_args[0][0]


class TestDownloadCaseFromParquet:
    """Tests for _download_case_from_parquet method."""

    def test_raises_data_load_error_on_malformed_data(self) -> None:
        """Test that _download_case_from_parquet raises DataLoadError for malformed data."""
        import pandas as pd  # type: ignore[import-untyped]

        case_ids = ["sub-stroke0001"]
        case_index = {"sub-stroke0001": 0}

        ds = HuggingFaceDataset(
            dataset_id="test/dataset",
            _case_ids=case_ids,
            _case_index=case_index,
        )

        # Create mock with missing 'bytes' key
        mock_df = pd.DataFrame(
            [
                {
                    "subject_id": "sub-stroke0001",
                    "dwi": {},  # Missing 'bytes'
                    "adc": {},
                    "lesion_mask": None,
                }
            ]
        )

        mock_table = MagicMock()
        mock_table.to_pandas.return_value = mock_df

        mock_pf = MagicMock()
        mock_pf.read.return_value = mock_table

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)

        mock_fs = MagicMock()
        mock_fs.open.return_value = mock_file

        # Patch at the source module where they're imported, not where they're used
        with (
            patch("huggingface_hub.HfFileSystem", return_value=mock_fs),
            patch("pyarrow.parquet.ParquetFile", return_value=mock_pf),
            pytest.raises(DataLoadError, match="Malformed HuggingFace data"),
        ):
            ds._download_case_from_parquet(0, "sub-stroke0001")
