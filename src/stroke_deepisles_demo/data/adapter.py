"""Provide typed access to ISLES24 cases."""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

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
    When get_case() is called, writes NIfTI bytes to temp files and returns paths.

    IMPORTANT: Use as a context manager to ensure temp files are cleaned up:

        with load_isles_dataset() as ds:
            case = ds.get_case(0)
            # ... process case ...
        # temp files automatically cleaned up

    Or call cleanup() manually when done.
    """

    dataset_id: str
    _hf_dataset: Any = field(repr=False)
    _case_ids: list[str] = field(default_factory=list)
    _temp_dir: Path | None = field(default=None, repr=False)
    _cached_cases: dict[str, CaseFiles] = field(default_factory=dict, repr=False)

    def __len__(self) -> int:
        return len(self._hf_dataset)

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

        Writes NIfTI bytes to temp files on first access; returns cached paths
        on subsequent calls for the same case.

        Raises:
            DataError: If HuggingFace data is malformed or missing required fields.
        """
        if isinstance(case_id, int):
            idx = case_id
            subject_id = self._case_ids[idx]
        else:
            subject_id = case_id
            idx = self._case_ids.index(subject_id)

        # Return cached case if already materialized
        if subject_id in self._cached_cases:
            return self._cached_cases[subject_id]

        # Create shared temp directory on first use
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="isles24_hf_"))
            logger.debug("Created temp directory: %s", self._temp_dir)

        # Get the HuggingFace example
        example = self._hf_dataset[idx]

        # Create case subdirectory
        case_dir = self._temp_dir / subject_id
        case_dir.mkdir(exist_ok=True)

        # Write NIfTI files to temp directory
        dwi_path = case_dir / f"{subject_id}_ses-02_dwi.nii.gz"
        adc_path = case_dir / f"{subject_id}_ses-02_adc.nii.gz"
        mask_path = case_dir / f"{subject_id}_ses-02_lesion-msk.nii.gz"

        # Extract bytes with defensive error handling
        try:
            dwi_bytes = example["dwi"]["bytes"]
            adc_bytes = example["adc"]["bytes"]
        except (KeyError, TypeError) as e:
            raise DataLoadError(
                f"Malformed HuggingFace data for {subject_id}: missing 'dwi' or 'adc' bytes. "
                f"The dataset schema may have changed. Error: {e}"
            ) from e

        # Write the gzipped NIfTI bytes
        dwi_path.write_bytes(dwi_bytes)
        adc_path.write_bytes(adc_bytes)

        case_files: CaseFiles = {
            "dwi": dwi_path,
            "adc": adc_path,
        }

        # Write lesion mask if available
        try:
            mask_data = example.get("lesion_mask")
            if mask_data and mask_data.get("bytes"):
                mask_path.write_bytes(mask_data["bytes"])
                case_files["ground_truth"] = mask_path
        except (KeyError, TypeError):
            # Mask is optional, log and continue
            logger.debug("No lesion mask available for %s", subject_id)

        # Cache for subsequent calls
        self._cached_cases[subject_id] = case_files

        return case_files

    def cleanup(self) -> None:
        """Remove temp directory and clear cache."""
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            logger.debug("Cleaned up temp directory: %s", self._temp_dir)
        self._temp_dir = None
        self._cached_cases.clear()


def build_huggingface_dataset(dataset_id: str) -> HuggingFaceDataset:
    """
    Load ISLES24 dataset from HuggingFace Hub.

    Args:
        dataset_id: HuggingFace dataset identifier (e.g., "hugging-science/isles24-stroke")

    Returns:
        HuggingFaceDataset providing case access
    """
    from datasets import load_dataset

    logger.info("Loading HuggingFace dataset: %s", dataset_id)
    hf_dataset = load_dataset(dataset_id, split="train")

    # Extract case IDs
    case_ids = [example["subject_id"] for example in hf_dataset]

    logger.info("Loaded %d cases from HuggingFace: %s", len(case_ids), dataset_id)

    return HuggingFaceDataset(
        dataset_id=dataset_id,
        _hf_dataset=hf_dataset,
        _case_ids=case_ids,
    )
