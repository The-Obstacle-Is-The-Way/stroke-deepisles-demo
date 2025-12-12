"""Data loading and case management for stroke-deepisles-demo."""

from stroke_deepisles_demo.core.types import CaseFiles
from stroke_deepisles_demo.data.adapter import LocalDataset
from stroke_deepisles_demo.data.loader import DatasetInfo, load_isles_dataset
from stroke_deepisles_demo.data.staging import StagedCase, stage_case_for_deepisles

__all__ = [
    "DatasetInfo",
    "LocalDataset",
    "StagedCase",
    "get_case",
    "list_case_ids",
    "load_isles_dataset",
    "stage_case_for_deepisles",
]


# Convenience functions (combine loader + adapter)
def get_case(case_id: str | int) -> CaseFiles:
    """
    Load a single case by ID or index.

    Uses context manager to ensure HuggingFace temp files are cleaned up.
    This prevents unbounded disk usage from accumulating temp NIfTI files.

    Returns:
        CaseFiles dictionary
    """
    with load_isles_dataset() as dataset:
        return dataset.get_case(case_id)


def list_case_ids() -> list[str]:
    """List all available case IDs.

    Uses context manager to ensure HuggingFace temp files are cleaned up.
    This prevents unbounded disk usage from accumulating temp NIfTI files.
    """
    with load_isles_dataset() as dataset:
        return dataset.list_case_ids()
