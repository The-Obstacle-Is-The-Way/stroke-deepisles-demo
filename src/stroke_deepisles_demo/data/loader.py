"""Load ISLES24 data from local directory or HuggingFace Hub."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, Self

if TYPE_CHECKING:
    from stroke_deepisles_demo.core.types import CaseFiles


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


# Default HuggingFace dataset ID
DEFAULT_HF_DATASET = "hugging-science/isles24-stroke"


def load_isles_dataset(
    source: str | Path | None = None,
    *,
    local_mode: bool | None = None,
) -> Dataset:
    """
    Load ISLES24 dataset from local directory or HuggingFace Hub.

    Args:
        source: Local directory path or HuggingFace dataset ID.
                If None, uses HuggingFace dataset by default.
        local_mode: If True, treat source as local directory.
                    If None, auto-detect based on source type.

    Returns:
        Dataset-like object providing case access. Use as context manager
        for automatic cleanup of temp files (important for HuggingFace mode).

    Examples:
        # Load from HuggingFace with automatic cleanup (recommended)
        with load_isles_dataset() as ds:
            case = ds.get_case(0)

        # Load from local directory
        ds = load_isles_dataset("data/isles24", local_mode=True)

        # Load specific HuggingFace dataset
        ds = load_isles_dataset("hugging-science/isles24-stroke")
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
    from stroke_deepisles_demo.data.adapter import build_huggingface_dataset

    dataset_id = source if source else DEFAULT_HF_DATASET
    return build_huggingface_dataset(str(dataset_id))
