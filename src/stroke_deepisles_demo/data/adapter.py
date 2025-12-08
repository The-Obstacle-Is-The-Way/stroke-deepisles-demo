"""Provide typed access to ISLES24 cases."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from stroke_deepisles_demo.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterator

    from stroke_deepisles_demo.core.types import CaseFiles

logger = get_logger(__name__)


@dataclass
class LocalDataset:
    """File-based dataset for local ISLES24 data."""

    data_dir: Path
    cases: dict[str, CaseFiles]  # subject_id -> files

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self) -> Iterator[str]:
        return iter(self.cases.keys())

    def list_case_ids(self) -> list[str]:
        """Return sorted list of subject IDs."""
        return sorted(self.cases.keys())

    def get_case(self, case_id: str | int) -> CaseFiles:
        """Get files for a case by ID or index."""
        if isinstance(case_id, int):
            case_id = self.list_case_ids()[case_id]
        return self.cases[case_id]


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
    """

    dataset_id: str
    _hf_dataset: Any = field(repr=False)
    _case_ids: list[str] = field(default_factory=list)
    _temp_dirs: list[Path] = field(default_factory=list, repr=False)

    def __len__(self) -> int:
        return len(self._hf_dataset)

    def __iter__(self) -> Iterator[str]:
        return iter(self._case_ids)

    def list_case_ids(self) -> list[str]:
        """Return sorted list of subject IDs."""
        return self._case_ids

    def get_case(self, case_id: str | int) -> CaseFiles:
        """Get files for a case by ID or index.

        Downloads NIfTI data from HuggingFace and writes to temp files.
        """
        if isinstance(case_id, int):
            idx = case_id
            subject_id = self._case_ids[idx]
        else:
            subject_id = case_id
            idx = self._case_ids.index(subject_id)

        # Get the HuggingFace example
        example = self._hf_dataset[idx]

        # Create temp directory for this case
        temp_dir = Path(tempfile.mkdtemp(prefix=f"isles24_{subject_id}_"))
        self._temp_dirs.append(temp_dir)

        # Write NIfTI files to temp directory
        dwi_path = temp_dir / f"{subject_id}_ses-02_dwi.nii.gz"
        adc_path = temp_dir / f"{subject_id}_ses-02_adc.nii.gz"
        mask_path = temp_dir / f"{subject_id}_ses-02_lesion-msk.nii.gz"

        # Write the gzipped NIfTI bytes
        dwi_path.write_bytes(example["dwi"]["bytes"])
        adc_path.write_bytes(example["adc"]["bytes"])

        case_files: CaseFiles = {
            "dwi": dwi_path,
            "adc": adc_path,
        }

        # Write lesion mask if available
        if example.get("lesion_mask") and example["lesion_mask"].get("bytes"):
            mask_path.write_bytes(example["lesion_mask"]["bytes"])
            case_files["ground_truth"] = mask_path

        return case_files

    def cleanup(self) -> None:
        """Remove all temp directories created by get_case()."""
        import shutil

        for temp_dir in self._temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
        self._temp_dirs.clear()


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
