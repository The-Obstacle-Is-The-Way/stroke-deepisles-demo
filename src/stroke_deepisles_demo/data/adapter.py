"""Adapt HF dataset rows to typed file references."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from stroke_deepisles_demo.core.exceptions import DataLoadError
from stroke_deepisles_demo.core.types import CaseFiles

if TYPE_CHECKING:
    from collections.abc import Iterator

    from datasets import Dataset


class CaseAdapter:
    """
    Adapts HuggingFace dataset to provide typed access to case files.

    This handles the mapping between HF dataset structure and our
    internal CaseFiles type.
    """

    def __init__(self, dataset: Dataset) -> None:
        """
        Initialize adapter with a loaded dataset.

        Args:
            dataset: HuggingFace Dataset with NIfTI files
        """
        self.dataset = dataset
        self._case_id_map = self._build_case_id_map()

    def _build_case_id_map(self) -> dict[str, int]:
        """Build mapping from case ID to index."""
        case_map = {}
        # Assuming dataset has 'participant_id' or similar
        # If not, we might need to generate IDs or use index

        # Check features to find ID column
        id_col = "participant_id"
        if id_col not in self.dataset.features:
            # Fallback: try to find a string column that looks like an ID
            # Or just use f"case_{i}"
            pass

        # Iterate to build map
        # This might be slow for huge datasets, but for 149 cases it's fine
        for idx, row in enumerate(self.dataset):
            case_id = row.get(id_col, f"case_{idx:03d}")
            case_map[str(case_id)] = idx

        return case_map

    def __len__(self) -> int:
        """Return number of cases in the dataset."""
        return len(self.dataset)

    def __iter__(self) -> Iterator[str]:
        """Iterate over case IDs."""
        return iter(self._case_id_map.keys())

    def list_case_ids(self) -> list[str]:
        """
        List all available case identifiers.

        Returns:
            List of case IDs (e.g., ["sub-001", "sub-002", ...])
        """
        return list(self._case_id_map.keys())

    def get_case(self, case_id: str | int) -> CaseFiles:
        """
        Get file paths for a specific case.

        Args:
            case_id: Either a string ID (e.g., "sub-001") or integer index

        Returns:
            CaseFiles with paths to DWI, ADC, and optionally ground truth

        Raises:
            KeyError: If case_id not found
            DataLoadError: If files cannot be accessed
        """
        if isinstance(case_id, int):
            index = case_id
        else:
            if case_id not in self._case_id_map:
                raise KeyError(f"Case ID not found: {case_id}")
            index = self._case_id_map[case_id]

        return self._get_case_by_index_internal(index)

    def get_case_by_index(self, index: int) -> tuple[str, CaseFiles]:
        """
        Get case by numerical index.

        Returns:
            Tuple of (case_id, CaseFiles)
        """
        if index < 0 or index >= len(self.dataset):
            raise IndexError("Case index out of range")

        # Find ID for index (reverse lookup)
        # This is inefficient O(N) if we don't store reverse map, but N is small.
        # Or we can just get it from row again.
        row = self.dataset[index]
        # Assuming 'participant_id' exists or we used fallback
        case_id = row.get("participant_id", f"case_{index:03d}")

        case_files = self._row_to_case_files(row)
        return str(case_id), case_files

    def _get_case_by_index_internal(self, index: int) -> CaseFiles:
        """Internal helper to get CaseFiles by index."""
        row = self.dataset[index]
        return self._row_to_case_files(row)

    def _row_to_case_files(self, row: dict[str, Any]) -> CaseFiles:
        """Convert a dataset row to CaseFiles."""
        # Map columns. DeepISLES needs DWI and ADC.
        # Dataset columns might vary. Based on spec/mock: 'dwi', 'adc', 'flair', 'mask'

        # Helper to ensure we return Path if it's a local string path, or keep as is
        def to_path_or_raw(val: Any) -> Any:
            if isinstance(val, str) and not val.startswith(("http://", "https://")):
                return Path(val)
            return val

        dwi = to_path_or_raw(row.get("dwi"))
        adc = to_path_or_raw(row.get("adc"))
        flair = to_path_or_raw(row.get("flair"))
        ground_truth = to_path_or_raw(row.get("mask") or row.get("ground_truth"))

        if not dwi or not adc:
            raise DataLoadError("Case missing required DWI or ADC files")

        case_files = CaseFiles(dwi=dwi, adc=adc)

        if flair:
            case_files["flair"] = flair
        if ground_truth:
            case_files["ground_truth"] = ground_truth

        return case_files
