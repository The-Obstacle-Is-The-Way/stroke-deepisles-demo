"""Stage NIfTI files with DeepISLES-expected naming."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from stroke_deepisles_demo.core.exceptions import MissingInputError

if TYPE_CHECKING:
    from stroke_deepisles_demo.core.types import CaseFiles


class StagedCase(NamedTuple):
    """Paths to staged files ready for DeepISLES."""

    input_dir: Path  # Directory containing staged files
    dwi_path: Path  # Path to dwi.nii.gz
    adc_path: Path  # Path to adc.nii.gz
    flair_path: Path | None  # Path to flair.nii.gz if available


def stage_case_for_deepisles(
    case_files: CaseFiles,
    output_dir: Path,
    *,
    case_id: str | None = None,
) -> StagedCase:
    """
    Stage case files with DeepISLES-expected naming convention.

    DeepISLES expects files named exactly:
    - dwi.nii.gz
    - adc.nii.gz
    - flair.nii.gz (optional)

    This function copies/symlinks the source files to a staging directory
    with the correct names.

    Args:
        case_files: Source file paths from CaseAdapter
        output_dir: Directory to stage files into
        case_id: Optional case ID for logging/subdirectory

    Returns:
        StagedCase with paths to staged files

    Raises:
        MissingInputError: If required files (DWI, ADC) are missing
        OSError: If file operations fail
    """
    # Create specific subdirectory if case_id provided, else use output_dir directly
    # The spec says "output_dir: Directory to stage files into".
    # If we append case_id, we might nest deeper than expected if output_dir is already specific.
    # Let's use output_dir as the container.

    stage_dir = output_dir
    if case_id:
        stage_dir = output_dir / case_id

    stage_dir.mkdir(parents=True, exist_ok=True)

    # DWI (Required)
    if "dwi" not in case_files or not case_files["dwi"]:
        raise MissingInputError("DWI file is required but missing from case files.")

    dwi_dest = stage_dir / "dwi.nii.gz"
    _materialize_nifti(case_files["dwi"], dwi_dest)

    # ADC (Required)
    if "adc" not in case_files or not case_files["adc"]:
        raise MissingInputError("ADC file is required but missing from case files.")

    adc_dest = stage_dir / "adc.nii.gz"
    _materialize_nifti(case_files["adc"], adc_dest)

    # FLAIR (Optional)
    flair_dest: Path | None = None
    if "flair" in case_files and case_files["flair"] is not None:
        flair_dest = stage_dir / "flair.nii.gz"
        _materialize_nifti(case_files["flair"], flair_dest)

    return StagedCase(
        input_dir=stage_dir,
        dwi_path=dwi_dest,
        adc_path=adc_dest,
        flair_path=flair_dest,
    )


def create_staging_directory(base_dir: Path | None = None) -> Path:
    """
    Create a temporary staging directory.

    Args:
        base_dir: Parent directory (uses system temp if None)

    Returns:
        Path to created staging directory
    """
    if base_dir:
        base_dir.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(dir=base_dir))
    return Path(tempfile.mkdtemp())


def _materialize_nifti(source: Path | str | bytes | Any, dest: Path) -> None:
    """
    Materialize a NIfTI file to a local path.

    Handles:
    - Local Path: copy
    - URL string: download (not implemented yet, placeholder)
    - bytes: write directly
    - NIfTI object: serialize with nibabel
    """
    if isinstance(source, Path):
        if not source.exists():
            raise MissingInputError(f"Source file does not exist: {source}")
        # Use copy2 to preserve metadata
        shutil.copy2(source, dest)
    elif isinstance(source, str):
        if source.startswith(("http://", "https://")):
            # TODO: Implement download logic or use requests
            # For now, we assume we don't hit this in offline tests
            raise NotImplementedError("URL download not yet implemented")
        else:
            # Assume local path string
            src_path = Path(source)
            if not src_path.exists():
                raise MissingInputError(f"Source file does not exist: {source}")
            shutil.copy2(src_path, dest)
    elif isinstance(source, bytes):
        dest.write_bytes(source)
    elif hasattr(source, "to_bytes"):
        # NIfTI object (nibabel image)
        # nibabel images don't strictly have to_bytes(), they have to_filename()
        # But datasets might wrap them.
        # If it's a nibabel image:
        if hasattr(source, "to_filename"):
            source.to_filename(dest)
        else:
            # Fallback for bytes-like
            dest.write_bytes(source.to_bytes())
    else:
        # If it's a lazy NIfTI object from datasets, it might be tricky.
        # Assuming mostly Path for now based on current tests.
        raise MissingInputError(f"Cannot materialize source of type: {type(source)}")
