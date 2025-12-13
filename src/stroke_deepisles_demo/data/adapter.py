"""Provide typed access to ISLES24 cases."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Self

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
