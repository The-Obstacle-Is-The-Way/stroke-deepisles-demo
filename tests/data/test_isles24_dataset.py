"""Unit tests for ISLES24 HF dataset fast-path loader."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.data.isles24_manifest import (
    ISLES24_DATASET_ID,
    ISLES24_DATASET_REVISION,
    ISLES24_TRAIN_CASE_IDS,
    isles24_train_data_file,
)
from stroke_deepisles_demo.data.loader import Isles24HuggingFaceDataset

if TYPE_CHECKING:
    from pathlib import Path


def test_list_case_ids_returns_manifest() -> None:
    dataset = Isles24HuggingFaceDataset()
    assert dataset.list_case_ids() == list(ISLES24_TRAIN_CASE_IDS)
    assert len(dataset) == len(ISLES24_TRAIN_CASE_IDS)


def test_get_case_loads_single_parquet_shard(tmp_path: Path) -> None:
    mock_dwi = MagicMock()
    mock_adc = MagicMock()

    mock_ds = MagicMock()
    mock_ds.select_columns.return_value = mock_ds
    mock_ds.__len__.return_value = 1
    mock_ds.__getitem__.return_value = {
        "subject_id": "sub-stroke0001",
        "dwi": mock_dwi,
        "adc": mock_adc,
        "lesion_mask": None,
    }

    temp_root = tmp_path / "hf_tmp"
    temp_root.mkdir()

    with (
        patch("datasets.load_dataset", return_value=mock_ds) as mock_load,
        patch("stroke_deepisles_demo.data.loader.tempfile.mkdtemp", return_value=str(temp_root)),
    ):
        dataset = Isles24HuggingFaceDataset(token="hf_token_123")
        with dataset:
            case = dataset.get_case("sub-stroke0001")

    # Uses pinned dataset settings + per-shard data_files selection.
    mock_load.assert_called_once_with(
        ISLES24_DATASET_ID,
        data_files={"train": isles24_train_data_file("sub-stroke0001")},
        split="train",
        token="hf_token_123",
        revision=ISLES24_DATASET_REVISION,
    )

    assert case["dwi"].name == "sub-stroke0001_dwi.nii.gz"
    assert case["adc"].name == "sub-stroke0001_adc.nii.gz"
    assert case["dwi"].parent == temp_root / "sub-stroke0001"
    assert case["adc"].parent == temp_root / "sub-stroke0001"

    # Materializes NIfTI objects via to_filename().
    assert mock_dwi.to_filename.call_count == 1
    assert mock_adc.to_filename.call_count == 1

    # Temp dir cleaned up by context manager.
    assert not temp_root.exists()


def test_get_case_rejects_unknown_case_id() -> None:
    dataset = Isles24HuggingFaceDataset()
    with pytest.raises(KeyError):
        _ = dataset.get_case("sub-stroke9999")
