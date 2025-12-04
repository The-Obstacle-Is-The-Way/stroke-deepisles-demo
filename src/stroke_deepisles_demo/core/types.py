"""Shared type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from pathlib import Path


class CaseFiles(TypedDict):
    """Paths to NIfTI files for a single case."""

    dwi: Path
    adc: Path
    flair: Path | None
    ground_truth: Path | None


@dataclass(frozen=True)
class InferenceResult:
    """Result of running DeepISLES on a case."""

    case_id: str
    input_files: CaseFiles
    prediction_mask: Path
    elapsed_seconds: float
