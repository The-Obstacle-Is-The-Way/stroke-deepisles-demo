"""Shared type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from pathlib import Path


class CaseFiles(TypedDict):
    """Paths to NIfTI files for a single case.

    Required keys:
        dwi: Path to DWI NIfTI file
        adc: Path to ADC NIfTI file

    Optional keys (may be absent):
        flair: Path to FLAIR NIfTI file (not all cases have FLAIR)
        ground_truth: Path to ground truth mask (not available during inference)
    """

    dwi: Path
    adc: Path
    flair: NotRequired[Path]
    ground_truth: NotRequired[Path]


@dataclass(frozen=True)
class InferenceResult:
    """Result of running DeepISLES on a case."""

    case_id: str
    input_files: CaseFiles
    prediction_mask: Path
    elapsed_seconds: float
