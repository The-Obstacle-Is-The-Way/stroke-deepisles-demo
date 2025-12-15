"""Load ISLES24 data from local directory or HuggingFace Hub."""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, Self

from stroke_deepisles_demo.core.logging import get_logger
from stroke_deepisles_demo.core.types import CaseFiles  # noqa: TC001
from stroke_deepisles_demo.data.isles24_manifest import (
    ISLES24_DATASET_ID,
    ISLES24_DATASET_REVISION,
    ISLES24_TRAIN_CASE_IDS,
    isles24_train_data_file,
)

# Security: Regex for valid ISLES24 subject IDs (defense-in-depth)
# Expected format: sub-strokeXXXX (e.g., sub-stroke0001)
_SAFE_SUBJECT_ID_PATTERN = re.compile(r"^sub-stroke\d{4}$")

if TYPE_CHECKING:
    from datasets import Dataset as HFDataset

logger = get_logger(__name__)


class Dataset(Protocol):
    """Protocol for dataset access.

    All dataset implementations support context manager usage for proper cleanup:

        with load_isles_dataset() as ds:
            case = ds.get_case(0)
            # ... process case ...
        # cleanup happens automatically
    """

    def __len__(self) -> int: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *args: object) -> None: ...
    def list_case_ids(self) -> list[str]: ...
    def get_case(self, case_id: str | int) -> CaseFiles: ...
    def cleanup(self) -> None: ...


@dataclass
class DatasetInfo:
    """Metadata about the dataset."""

    source: str  # "local" or HF dataset ID
    num_cases: int
    modalities: list[str]
    has_ground_truth: bool


@dataclass
class HuggingFaceDatasetWrapper:
    """Wrapper for HuggingFace dataset to match the Dataset protocol.

    Uses the standard datasets library (with neuroimaging-go-brrrr patched Nifti feature)
    to load data. Materializes NIfTI images to temporary files on demand.
    """

    dataset: HFDataset
    dataset_id: str
    _temp_dir: Path | None = field(default=None, repr=False)
    _case_id_to_index: dict[str, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Build index of subject IDs for O(1) lookup."""
        try:
            # Efficiently build index from 'subject_id' column
            self._case_id_to_index = {
                sid: idx for idx, sid in enumerate(self.dataset["subject_id"])
            }
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(
                "Failed to build index from subject_id column: %s. Fallback to iteration.", e
            )
            for idx, item in enumerate(self.dataset):
                self._case_id_to_index[item["subject_id"]] = idx

    def __len__(self) -> int:
        return len(self.dataset)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.cleanup()

    def list_case_ids(self) -> list[str]:
        return sorted(self._case_id_to_index.keys())

    def get_case(self, case_id: str | int) -> CaseFiles:
        """Get files for a case by ID or index.

        Materializes NIfTI objects to temporary files.
        """
        # Resolve case_id to index
        if isinstance(case_id, int):
            if case_id < 0 or case_id >= len(self.dataset):
                raise IndexError(f"Case index {case_id} out of range")
            idx = case_id
        else:
            if case_id not in self._case_id_to_index:
                raise KeyError(f"Case ID {case_id} not found")
            idx = self._case_id_to_index[case_id]

        row = self.dataset[idx]
        subject_id = row["subject_id"]

        # Security: Validate subject_id before using in path (defense-in-depth)
        if not _SAFE_SUBJECT_ID_PATTERN.match(subject_id):
            raise ValueError(
                f"Invalid subject_id format: {subject_id!r}. Expected format: sub-strokeXXXX"
            )

        # Prepare temp dir
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="isles24_hf_wrapper_"))

        case_dir = self._temp_dir / subject_id
        case_dir.mkdir(exist_ok=True)

        dwi_path = case_dir / f"{subject_id}_dwi.nii.gz"
        adc_path = case_dir / f"{subject_id}_adc.nii.gz"

        # Materialize files if they don't exist
        if not dwi_path.exists():
            row["dwi"].to_filename(str(dwi_path))

        if not adc_path.exists():
            row["adc"].to_filename(str(adc_path))

        case_files: CaseFiles = {
            "dwi": dwi_path,
            "adc": adc_path,
        }

        # Handle lesion mask (mapped to ground_truth)
        if "lesion_mask" in row and row["lesion_mask"] is not None:
            mask_path = case_dir / f"{subject_id}_lesion-msk.nii.gz"
            if not mask_path.exists():
                row["lesion_mask"].to_filename(str(mask_path))
            case_files["ground_truth"] = mask_path

        return case_files

    def cleanup(self) -> None:
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
            except OSError as e:
                logger.warning("Failed to cleanup temp directory %s: %s", self._temp_dir, e)
        self._temp_dir = None


@dataclass
class Isles24HuggingFaceDataset:
    """ISLES24 dataset access optimized for HF Spaces.

    Key behavior:
    - `list_case_ids()` returns from a pinned manifest (no dataset download).
    - `get_case()` loads exactly one Parquet shard via `data_files=...` (no 27GB eager download).

    This class exists because `datasets.load_dataset(dataset_id, split="train")` can
    trigger an eager full-dataset download/prepare on cold starts, which is not viable
    for API endpoints like `/api/cases` on Hugging Face Spaces.
    """

    dataset_id: str = ISLES24_DATASET_ID
    token: str | None = None
    revision: str = ISLES24_DATASET_REVISION
    _temp_dir: Path | None = field(default=None, repr=False)

    def __len__(self) -> int:
        return len(ISLES24_TRAIN_CASE_IDS)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.cleanup()

    def list_case_ids(self) -> list[str]:
        return list(ISLES24_TRAIN_CASE_IDS)

    def get_case(self, case_id: str | int) -> CaseFiles:
        """Load files for a single ISLES24 case.

        Args:
            case_id: Case identifier (e.g., "sub-stroke0102") or 0-based integer index.
        """
        from datasets import load_dataset

        if isinstance(case_id, int):
            if case_id < 0 or case_id >= len(ISLES24_TRAIN_CASE_IDS):
                raise IndexError(f"Case index {case_id} out of range")
            resolved_case_id = ISLES24_TRAIN_CASE_IDS[case_id]
        else:
            resolved_case_id = case_id

        # Security: Validate subject_id before using in path (defense-in-depth)
        if not _SAFE_SUBJECT_ID_PATTERN.match(resolved_case_id):
            raise ValueError(
                f"Invalid subject_id format: {resolved_case_id!r}. Expected format: sub-strokeXXXX"
            )

        # Load exactly one shard (1 case per parquet file in this dataset)
        data_file = isles24_train_data_file(resolved_case_id)
        ds = load_dataset(
            self.dataset_id,
            data_files={"train": data_file},
            split="train",
            token=self.token,
            revision=self.revision,
        )
        ds = ds.select_columns(["subject_id", "dwi", "adc", "lesion_mask"])
        if len(ds) != 1:
            raise RuntimeError(f"Expected 1 row for {resolved_case_id}, got {len(ds)}")

        row = ds[0]
        subject_id = row["subject_id"]
        if subject_id != resolved_case_id:
            raise RuntimeError(
                f"Unexpected subject_id {subject_id!r} in {data_file} (expected {resolved_case_id!r})"
            )

        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="isles24_hf_wrapper_"))

        case_dir = self._temp_dir / subject_id
        case_dir.mkdir(exist_ok=True)

        dwi_path = case_dir / f"{subject_id}_dwi.nii.gz"
        adc_path = case_dir / f"{subject_id}_adc.nii.gz"

        if not dwi_path.exists():
            row["dwi"].to_filename(str(dwi_path))
        if not adc_path.exists():
            row["adc"].to_filename(str(adc_path))

        case_files: CaseFiles = {
            "dwi": dwi_path,
            "adc": adc_path,
        }

        if row.get("lesion_mask") is not None:
            mask_path = case_dir / f"{subject_id}_lesion-msk.nii.gz"
            if not mask_path.exists():
                row["lesion_mask"].to_filename(str(mask_path))
            case_files["ground_truth"] = mask_path

        return case_files

    def cleanup(self) -> None:
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
            except OSError as e:
                logger.warning("Failed to cleanup temp directory %s: %s", self._temp_dir, e)
        self._temp_dir = None


def load_isles_dataset(
    source: str | Path | None = None,
    *,
    local_mode: bool | None = None,
    token: str | None = None,
) -> Dataset:
    """
    Load ISLES24 dataset from local directory or HuggingFace Hub.

    Args:
        source: Local directory path or HuggingFace dataset ID.
                If None, uses Settings.hf_dataset_id from config.
        local_mode: If True, treat source as local directory.
                    If None, auto-detect based on source type.
        token: HuggingFace token for private/gated datasets.
               If None, uses Settings.hf_token from config.

    Returns:
        Dataset-like object providing case access. Use as context manager
        for automatic cleanup of temp files (important for HuggingFace mode).

    Examples:
        # Load from HuggingFace with automatic cleanup (recommended)
        with load_isles_dataset() as ds:
            case = ds.get_case(0)

        # Load from local directory
        ds = load_isles_dataset("data/isles24", local_mode=True)

        # Load specific HuggingFace dataset with token
        ds = load_isles_dataset("org/private-dataset", token="hf_xxx")
    """
    # Auto-detect mode if not specified
    if local_mode is None:
        if source is None:
            local_mode = False  # Default to HuggingFace
        elif isinstance(source, Path):
            local_mode = True
        else:
            # String: check if it's an existing local path
            # Only select local mode if the path itself exists
            # (avoids misclassifying HF dataset IDs like "org/dataset")
            source_path = Path(source)
            local_mode = source_path.exists()

    if local_mode:
        from stroke_deepisles_demo.data.adapter import build_local_dataset

        if source is None:
            source = "data/isles24"
        return build_local_dataset(Path(source))

    # HuggingFace mode
    from datasets import load_dataset

    from stroke_deepisles_demo.core.config import get_settings

    settings = get_settings()

    # Use settings defaults if not specified
    dataset_id = str(source) if source else settings.hf_dataset_id
    hf_token = token if token is not None else settings.hf_token

    if dataset_id == ISLES24_DATASET_ID:
        return Isles24HuggingFaceDataset(dataset_id=dataset_id, token=hf_token)

    # Load dataset, selecting only necessary columns to minimize decoding overhead
    # We rely on neuroimaging-go-brrrr's Nifti feature for lazy loading if configured,
    # but select_columns ensures we don't touch other modalities.
    # Token enables access to private/gated datasets
    ds = load_dataset(dataset_id, split="train", token=hf_token)
    ds = ds.select_columns(["subject_id", "dwi", "adc", "lesion_mask"])

    return HuggingFaceDatasetWrapper(ds, dataset_id)
