"""Load ISLES24 data from local directory or HuggingFace Hub."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stroke_deepisles_demo.data.adapter import LocalDataset


@dataclass
class DatasetInfo:
    """Metadata about the dataset."""

    source: str  # "local" or HF dataset ID
    num_cases: int
    modalities: list[str]
    has_ground_truth: bool


def load_isles_dataset(
    source: str | Path = "data/isles24",
    *,
    local_mode: bool = True,  # Default to local for now
) -> LocalDataset:
    """
    Load ISLES24 dataset.

    Args:
        source: Local directory path or HuggingFace dataset ID
        local_mode: If True, treat source as local directory

    Returns:
        Dataset-like object providing case access

    Raises:
        NotImplementedError: If non-local mode is requested
    """
    if local_mode or isinstance(source, Path):
        from stroke_deepisles_demo.data.adapter import build_local_dataset

        return build_local_dataset(Path(source))

    # Future: return _load_from_huggingface(source)
    raise NotImplementedError("HuggingFace mode not yet implemented")
