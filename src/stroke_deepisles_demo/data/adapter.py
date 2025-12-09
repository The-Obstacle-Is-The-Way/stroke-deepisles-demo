"""Provide typed access to ISLES24 cases."""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Self

from stroke_deepisles_demo.core.exceptions import DataLoadError
from stroke_deepisles_demo.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterator

    from stroke_deepisles_demo.core.types import CaseFiles

logger = get_logger(__name__)


@dataclass
class LocalDataset:
    """File-based dataset for local ISLES24 data.

    Can be used as a context manager for consistency with HuggingFaceDataset,
    though no cleanup is needed for local files.

    Example:
        with build_local_dataset(path) as ds:
            case = ds.get_case(0)
    """

    data_dir: Path
    cases: dict[str, CaseFiles]  # subject_id -> files

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self) -> Iterator[str]:
        return iter(self.cases.keys())

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        # No cleanup needed for local files
        pass

    def list_case_ids(self) -> list[str]:
        """Return sorted list of subject IDs."""
        return sorted(self.cases.keys())

    def get_case(self, case_id: str | int) -> CaseFiles:
        """Get files for a case by ID or index."""
        if isinstance(case_id, int):
            case_id = self.list_case_ids()[case_id]
        return self.cases[case_id]

    def cleanup(self) -> None:
        """No-op for local dataset (files are not temporary)."""
        pass


# Subject ID extraction
SUBJECT_PATTERN = re.compile(r"sub-(stroke\d{4})_ses-\d+_.*\.nii\.gz")


def parse_subject_id(filename: str) -> str | None:
    """Extract subject ID from BIDS filename."""
    match = SUBJECT_PATTERN.match(filename)
    return f"sub-{match.group(1)}" if match else None


def build_local_dataset(data_dir: Path) -> LocalDataset:
    """
    Scan directory and build case mapping.

    Matches DWI + ADC + Mask files by subject ID.
    Logs warnings for incomplete cases that are skipped.

    Raises:
        FileNotFoundError: If DWI subdirectory (Images-DWI) is missing
    """
    dwi_dir = data_dir / "Images-DWI"
    adc_dir = data_dir / "Images-ADC"
    mask_dir = data_dir / "Masks"

    if not dwi_dir.exists():
        raise FileNotFoundError(f"Data directory not found or invalid: {dwi_dir}")

    cases: dict[str, CaseFiles] = {}
    skipped_no_subject_id = 0
    skipped_no_adc: list[str] = []

    # Scan DWI files to get subject IDs
    for dwi_file in dwi_dir.glob("*.nii.gz"):
        subject_id = parse_subject_id(dwi_file.name)
        if not subject_id:
            skipped_no_subject_id += 1
            continue

        # Find matching ADC and Mask
        adc_file = adc_dir / dwi_file.name.replace("_dwi.", "_adc.")
        mask_file = mask_dir / dwi_file.name.replace("_dwi.", "_lesion-msk.")

        if not adc_file.exists():
            skipped_no_adc.append(subject_id)
            continue

        case_files: CaseFiles = {
            "dwi": dwi_file,
            "adc": adc_file,
        }
        if mask_file.exists():
            case_files["ground_truth"] = mask_file

        cases[subject_id] = case_files

    # Log skipped cases for debugging
    if skipped_no_subject_id > 0:
        logger.warning(
            "Skipped %d DWI files: could not parse subject ID from filename",
            skipped_no_subject_id,
        )
    if skipped_no_adc:
        logger.warning(
            "Skipped %d cases missing ADC file: %s",
            len(skipped_no_adc),
            ", ".join(skipped_no_adc[:5]) + ("..." if len(skipped_no_adc) > 5 else ""),
        )

    logger.info("Loaded %d cases from %s", len(cases), data_dir)
    return LocalDataset(data_dir=data_dir, cases=cases)


# =============================================================================
# HuggingFace Dataset Adapter
# =============================================================================


@dataclass
class HuggingFaceDataset:
    """Dataset adapter for HuggingFace ISLES24 dataset.

    Wraps the HuggingFace dataset and provides the same interface as LocalDataset.
    When get_case() is called, downloads NIfTI bytes from individual parquet files
    and writes them to temp files.

    This implementation bypasses `load_dataset()` entirely to avoid:
    1. PyArrow streaming bug (apache/arrow#45214) that hangs on parquet iteration
    2. Memory issues from downloading the full 99GB dataset

    IMPORTANT: Use as a context manager to ensure temp files are cleaned up:

        with build_huggingface_dataset(dataset_id) as ds:
            case = ds.get_case(0)
            # ... process case ...
        # temp files automatically cleaned up

    Or call cleanup() manually when done.
    """

    dataset_id: str
    _case_ids: list[str] = field(default_factory=list)
    _case_index: dict[str, int] = field(default_factory=dict)
    _temp_dir: Path | None = field(default=None, repr=False)
    _cached_cases: dict[str, CaseFiles] = field(default_factory=dict, repr=False)

    def __len__(self) -> int:
        return len(self._case_ids)

    def __iter__(self) -> Iterator[str]:
        return iter(self._case_ids)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.cleanup()

    def list_case_ids(self) -> list[str]:
        """Return sorted list of subject IDs."""
        return sorted(self._case_ids)

    def get_case(self, case_id: str | int) -> CaseFiles:
        """Get files for a case by ID or index.

        Downloads NIfTI bytes from the individual parquet file for this case
        and writes to temp files. Returns cached paths on subsequent calls.

        This uses HfFileSystem + pyarrow to download only the single case (~50MB)
        instead of the full dataset (99GB), completing in ~2 seconds.

        Raises:
            DataLoadError: If HuggingFace data is malformed or missing required fields.
            KeyError: If case_id is not found in the dataset.
        """
        # Resolve case_id to subject_id and file index
        if isinstance(case_id, int):
            if case_id < 0 or case_id >= len(self._case_ids):
                raise IndexError(f"Case index {case_id} out of range [0, {len(self._case_ids)})")
            subject_id = self._case_ids[case_id]
            file_idx = case_id
        else:
            subject_id = case_id
            if subject_id not in self._case_index:
                raise KeyError(f"Case ID '{subject_id}' not found in dataset")
            file_idx = self._case_index[subject_id]

        # Return cached case if already materialized
        if subject_id in self._cached_cases:
            return self._cached_cases[subject_id]

        # Create shared temp directory on first use
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="isles24_hf_"))
            logger.debug("Created temp directory: %s", self._temp_dir)

        # Download case data from individual parquet file
        logger.info("Downloading case %s from HuggingFace...", subject_id)
        case_data = self._download_case_from_parquet(file_idx, subject_id)

        # Create case subdirectory
        case_dir = self._temp_dir / subject_id
        case_dir.mkdir(exist_ok=True)

        # Write NIfTI files to temp directory
        dwi_path = case_dir / f"{subject_id}_ses-02_dwi.nii.gz"
        adc_path = case_dir / f"{subject_id}_ses-02_adc.nii.gz"
        mask_path = case_dir / f"{subject_id}_ses-02_lesion-msk.nii.gz"

        # Write the gzipped NIfTI bytes
        dwi_path.write_bytes(case_data["dwi_bytes"])
        adc_path.write_bytes(case_data["adc_bytes"])

        case_files: CaseFiles = {
            "dwi": dwi_path,
            "adc": adc_path,
        }

        # Write lesion mask if available
        if case_data.get("mask_bytes"):
            mask_path.write_bytes(case_data["mask_bytes"])
            case_files["ground_truth"] = mask_path

        # Cache for subsequent calls
        self._cached_cases[subject_id] = case_files
        logger.info(
            "Case %s ready: DWI=%.1fMB, ADC=%.1fMB",
            subject_id,
            len(case_data["dwi_bytes"]) / 1024 / 1024,
            len(case_data["adc_bytes"]) / 1024 / 1024,
        )

        return case_files

    def _download_case_from_parquet(self, file_idx: int, subject_id: str) -> dict[str, bytes]:
        """Download case data directly from individual parquet file.

        Uses HfFileSystem + pyarrow to read only the columns we need from
        a single parquet file, avoiding the need to download the full dataset.

        Args:
            file_idx: Index of the parquet file (0-148)
            subject_id: Expected subject ID (for validation)

        Returns:
            Dict with dwi_bytes, adc_bytes, and optionally mask_bytes
        """
        import pyarrow.parquet as pq  # type: ignore[import-untyped]
        from huggingface_hub import HfFileSystem

        from stroke_deepisles_demo.data.constants import ISLES24_NUM_FILES

        # Construct path to the specific parquet file
        fpath = f"datasets/{self.dataset_id}/data/train-{file_idx:05d}-of-{ISLES24_NUM_FILES:05d}.parquet"

        try:
            fs = HfFileSystem()
            with fs.open(fpath, "rb") as f:
                pf = pq.ParquetFile(f)
                # Read only the columns we need
                table = pf.read(columns=["subject_id", "dwi", "adc", "lesion_mask"])
                df = table.to_pandas()

                if len(df) != 1:
                    raise DataLoadError(f"Expected 1 row in parquet file, got {len(df)}: {fpath}")

                row = df.iloc[0]

                # Validate subject_id matches
                actual_subject_id = row["subject_id"]
                if actual_subject_id != subject_id:
                    raise DataLoadError(
                        f"Subject ID mismatch: expected {subject_id}, got {actual_subject_id} in {fpath}"
                    )

                # Extract bytes with defensive error handling
                try:
                    dwi_bytes = row["dwi"]["bytes"]
                    adc_bytes = row["adc"]["bytes"]
                except (KeyError, TypeError) as e:
                    raise DataLoadError(
                        f"Malformed HuggingFace data for {subject_id}: missing 'dwi' or 'adc' bytes. "
                        f"The dataset schema may have changed. Error: {e}"
                    ) from e

                result: dict[str, bytes] = {
                    "dwi_bytes": dwi_bytes,
                    "adc_bytes": adc_bytes,
                }

                # Extract mask if available
                mask_data = row.get("lesion_mask")
                if mask_data is not None and isinstance(mask_data, dict) and mask_data.get("bytes"):
                    result["mask_bytes"] = mask_data["bytes"]

                return result

        except Exception as e:
            if isinstance(e, DataLoadError):
                raise
            raise DataLoadError(f"Failed to download case {subject_id} from {fpath}: {e}") from e

    def cleanup(self) -> None:
        """Remove temp directory and clear cache."""
        if self._temp_dir is not None and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                logger.debug("Cleaned up temp directory: %s", self._temp_dir)
            except OSError as e:
                logger.warning("Failed to cleanup temp directory %s: %s", self._temp_dir, e)
        self._temp_dir = None
        self._cached_cases.clear()


def build_huggingface_dataset(dataset_id: str) -> HuggingFaceDataset:
    """
    Build ISLES24 dataset adapter for HuggingFace Hub.

    Uses pre-computed case IDs to avoid streaming enumeration (which hangs
    due to PyArrow bug apache/arrow#45214). Actual data is downloaded lazily
    from individual parquet files when get_case() is called.

    Args:
        dataset_id: HuggingFace dataset identifier (e.g., "hugging-science/isles24-stroke")

    Returns:
        HuggingFaceDataset providing case access
    """
    from stroke_deepisles_demo.data.constants import (
        ISLES24_CASE_IDS,
        ISLES24_CASE_INDEX,
        ISLES24_DATASET_ID,
    )

    # Validate dataset_id matches our pre-computed constants
    if dataset_id != ISLES24_DATASET_ID:
        logger.warning(
            "Dataset ID '%s' does not match pre-computed constants for '%s'. "
            "Case IDs may be incorrect.",
            dataset_id,
            ISLES24_DATASET_ID,
        )

    logger.info(
        "Building HuggingFace dataset adapter: %s (%d cases, pre-computed)",
        dataset_id,
        len(ISLES24_CASE_IDS),
    )

    return HuggingFaceDataset(
        dataset_id=dataset_id,
        _case_ids=list(ISLES24_CASE_IDS),
        _case_index=dict(ISLES24_CASE_INDEX),
    )
