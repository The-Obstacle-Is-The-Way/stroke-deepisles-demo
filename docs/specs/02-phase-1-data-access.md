# phase 1: data access / hf integration

## purpose

Implement the data loading layer that consumes ISLES24-MR-Lite from HuggingFace Hub. At the end of this phase, we can load any case by ID and get local paths to DWI, ADC, and ground truth NIfTI files.

## deliverables

- [ ] `src/stroke_deepisles_demo/data/loader.py` - HF dataset loading
- [ ] `src/stroke_deepisles_demo/data/adapter.py` - Case adapter for file access
- [ ] `src/stroke_deepisles_demo/data/staging.py` - Stage files for DeepISLES
- [ ] Unit tests with fixtures (no network required)
- [ ] Integration test (marked, requires network)

## vertical slice outcome

After this phase, you can run:

```python
from stroke_deepisles_demo.data import get_case, list_case_ids

# List available cases
case_ids = list_case_ids()
print(f"Found {len(case_ids)} cases")

# Load a specific case
case = get_case("sub-001")
print(f"DWI: {case.dwi}")
print(f"ADC: {case.adc}")
print(f"Ground truth: {case.ground_truth}")
```

## module structure

```
src/stroke_deepisles_demo/data/
├── __init__.py          # Public API exports
├── loader.py            # HF Hub dataset loading
├── adapter.py           # Case adapter (index → files)
└── staging.py           # Stage files with DeepISLES naming
```

## interfaces and types

### `data/loader.py`

```python
"""Load ISLES24-MR-Lite dataset from HuggingFace Hub."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datasets import Dataset


def load_isles_dataset(
    dataset_id: str = "YongchengYAO/ISLES24-MR-Lite",
    *,
    cache_dir: Path | None = None,
    streaming: bool = False,
) -> Dataset:
    """
    Load the ISLES24-MR-Lite dataset from HuggingFace Hub.

    Args:
        dataset_id: HuggingFace dataset identifier
        cache_dir: Local cache directory (uses HF default if None)
        streaming: If True, use streaming mode (lazy loading)

    Returns:
        HuggingFace Dataset object with BIDS/NIfTI support

    Raises:
        DataLoadError: If dataset cannot be loaded
    """
    ...


def get_dataset_info(dataset_id: str = "YongchengYAO/ISLES24-MR-Lite") -> DatasetInfo:
    """
    Get metadata about the dataset without downloading.

    Returns:
        DatasetInfo with case count, available modalities, etc.
    """
    ...


@dataclass
class DatasetInfo:
    """Metadata about the loaded dataset."""

    dataset_id: str
    num_cases: int
    modalities: list[str]  # e.g., ["dwi", "adc", "mask"]
    has_ground_truth: bool
```

### `data/adapter.py`

```python
"""Adapt HF dataset rows to typed file references."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from stroke_deepisles_demo.core.types import CaseFiles


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
        ...

    def __len__(self) -> int:
        """Return number of cases in the dataset."""
        ...

    def __iter__(self) -> Iterator[str]:
        """Iterate over case IDs."""
        ...

    def list_case_ids(self) -> list[str]:
        """
        List all available case identifiers.

        Returns:
            List of case IDs (e.g., ["sub-001", "sub-002", ...])
        """
        ...

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
        ...

    def get_case_by_index(self, index: int) -> tuple[str, CaseFiles]:
        """
        Get case by numerical index.

        Returns:
            Tuple of (case_id, CaseFiles)
        """
        ...
```

### `data/staging.py`

```python
"""Stage NIfTI files with DeepISLES-expected naming."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from stroke_deepisles_demo.core.types import CaseFiles


class StagedCase(NamedTuple):
    """Paths to staged files ready for DeepISLES."""

    input_dir: Path      # Directory containing staged files
    dwi_path: Path       # Path to dwi.nii.gz
    adc_path: Path       # Path to adc.nii.gz
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
    ...


def create_staging_directory(base_dir: Path | None = None) -> Path:
    """
    Create a temporary staging directory.

    Args:
        base_dir: Parent directory (uses system temp if None)

    Returns:
        Path to created staging directory
    """
    ...
```

### `data/__init__.py` (public API)

```python
"""Data loading and case management for stroke-deepisles-demo."""

from stroke_deepisles_demo.data.adapter import CaseAdapter
from stroke_deepisles_demo.data.loader import DatasetInfo, get_dataset_info, load_isles_dataset
from stroke_deepisles_demo.data.staging import StagedCase, stage_case_for_deepisles

__all__ = [
    # Loader
    "load_isles_dataset",
    "get_dataset_info",
    "DatasetInfo",
    # Adapter
    "CaseAdapter",
    # Staging
    "stage_case_for_deepisles",
    "StagedCase",
]


# Convenience functions (combine loader + adapter)
def get_case(case_id: str | int) -> CaseFiles:
    """Load a single case by ID or index."""
    ...


def list_case_ids() -> list[str]:
    """List all available case IDs."""
    ...
```

## tdd plan

### test file structure

```
tests/
├── conftest.py              # Shared fixtures
├── data/
│   ├── __init__.py
│   ├── test_loader.py       # Tests for HF loading
│   ├── test_adapter.py      # Tests for case adapter
│   └── test_staging.py      # Tests for file staging
└── fixtures/
    └── nifti/               # Minimal synthetic NIfTI files
        ├── dwi.nii.gz
        ├── adc.nii.gz
        └── mask.nii.gz
```

### tests to write first (TDD order)

#### 1. `tests/conftest.py` - Fixtures

```python
"""Shared test fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def synthetic_nifti_3d(temp_dir: Path) -> Path:
    """Create a minimal synthetic 3D NIfTI file."""
    data = np.random.rand(10, 10, 10).astype(np.float32)
    img = nib.Nifti1Image(data, affine=np.eye(4))
    path = temp_dir / "synthetic.nii.gz"
    nib.save(img, path)
    return path


@pytest.fixture
def synthetic_case_files(temp_dir: Path) -> CaseFiles:
    """Create a complete set of synthetic case files."""
    # Create DWI
    dwi_data = np.random.rand(64, 64, 30).astype(np.float32)
    dwi_img = nib.Nifti1Image(dwi_data, affine=np.eye(4))
    dwi_path = temp_dir / "dwi.nii.gz"
    nib.save(dwi_img, dwi_path)

    # Create ADC
    adc_data = np.random.rand(64, 64, 30).astype(np.float32) * 2000
    adc_img = nib.Nifti1Image(adc_data, affine=np.eye(4))
    adc_path = temp_dir / "adc.nii.gz"
    nib.save(adc_img, adc_path)

    # Create mask
    mask_data = (np.random.rand(64, 64, 30) > 0.9).astype(np.uint8)
    mask_img = nib.Nifti1Image(mask_data, affine=np.eye(4))
    mask_path = temp_dir / "mask.nii.gz"
    nib.save(mask_img, mask_path)

    return CaseFiles(
        dwi=dwi_path,
        adc=adc_path,
        flair=None,
        ground_truth=mask_path,
    )


@pytest.fixture
def mock_hf_dataset(synthetic_case_files: CaseFiles):
    """Create a mock HF Dataset-like object."""
    # Returns a simple dict-based mock that mimics Dataset behavior
    ...
```

#### 2. `tests/data/test_staging.py` - Start with staging (no network)

```python
"""Tests for data staging module."""

from __future__ import annotations

from pathlib import Path

import pytest

from stroke_deepisles_demo.core.exceptions import MissingInputError
from stroke_deepisles_demo.core.types import CaseFiles
from stroke_deepisles_demo.data.staging import (
    StagedCase,
    create_staging_directory,
    stage_case_for_deepisles,
)


class TestCreateStagingDirectory:
    """Tests for create_staging_directory."""

    def test_creates_directory(self, temp_dir: Path) -> None:
        """Staging directory is created and exists."""
        staging = create_staging_directory(base_dir=temp_dir)
        assert staging.exists()
        assert staging.is_dir()

    def test_uses_system_temp_when_no_base(self) -> None:
        """Uses system temp directory when base_dir is None."""
        staging = create_staging_directory(base_dir=None)
        assert staging.exists()
        # Cleanup
        staging.rmdir()


class TestStageCaseForDeepIsles:
    """Tests for stage_case_for_deepisles."""

    def test_stages_required_files(
        self, synthetic_case_files: CaseFiles, temp_dir: Path
    ) -> None:
        """DWI and ADC are staged with correct names."""
        staged = stage_case_for_deepisles(synthetic_case_files, temp_dir)

        assert staged.dwi_path.name == "dwi.nii.gz"
        assert staged.adc_path.name == "adc.nii.gz"
        assert staged.dwi_path.exists()
        assert staged.adc_path.exists()

    def test_staged_files_are_readable(
        self, synthetic_case_files: CaseFiles, temp_dir: Path
    ) -> None:
        """Staged files can be read as valid NIfTI."""
        import nibabel as nib

        staged = stage_case_for_deepisles(synthetic_case_files, temp_dir)

        dwi = nib.load(staged.dwi_path)
        assert dwi.shape == (64, 64, 30)

    def test_raises_when_dwi_missing(self, temp_dir: Path) -> None:
        """Raises MissingInputError when DWI is missing."""
        case_files = CaseFiles(
            dwi=temp_dir / "nonexistent.nii.gz",
            adc=temp_dir / "adc.nii.gz",
            flair=None,
            ground_truth=None,
        )

        with pytest.raises(MissingInputError, match="DWI"):
            stage_case_for_deepisles(case_files, temp_dir)

    def test_flair_is_optional(
        self, synthetic_case_files: CaseFiles, temp_dir: Path
    ) -> None:
        """Staging succeeds when FLAIR is None."""
        # synthetic_case_files has flair=None
        staged = stage_case_for_deepisles(synthetic_case_files, temp_dir)

        assert staged.flair_path is None
```

#### 3. `tests/data/test_adapter.py` - Case adapter with mocks

```python
"""Tests for case adapter module."""

from __future__ import annotations

import pytest

from stroke_deepisles_demo.core.types import CaseFiles
from stroke_deepisles_demo.data.adapter import CaseAdapter


class TestCaseAdapter:
    """Tests for CaseAdapter."""

    def test_list_case_ids_returns_strings(self, mock_hf_dataset) -> None:
        """list_case_ids returns list of string identifiers."""
        adapter = CaseAdapter(mock_hf_dataset)
        case_ids = adapter.list_case_ids()

        assert isinstance(case_ids, list)
        assert all(isinstance(cid, str) for cid in case_ids)

    def test_len_matches_dataset_size(self, mock_hf_dataset) -> None:
        """len(adapter) equals number of cases in dataset."""
        adapter = CaseAdapter(mock_hf_dataset)

        assert len(adapter) == len(mock_hf_dataset)

    def test_get_case_by_string_id(self, mock_hf_dataset) -> None:
        """Can retrieve case by string identifier."""
        adapter = CaseAdapter(mock_hf_dataset)
        case_ids = adapter.list_case_ids()

        case = adapter.get_case(case_ids[0])

        assert isinstance(case, dict)  # CaseFiles is a TypedDict
        assert "dwi" in case
        assert "adc" in case

    def test_get_case_by_index(self, mock_hf_dataset) -> None:
        """Can retrieve case by integer index."""
        adapter = CaseAdapter(mock_hf_dataset)

        case_id, case = adapter.get_case_by_index(0)

        assert isinstance(case_id, str)
        assert case["dwi"] is not None

    def test_get_case_invalid_id_raises(self, mock_hf_dataset) -> None:
        """Raises KeyError for invalid case ID."""
        adapter = CaseAdapter(mock_hf_dataset)

        with pytest.raises(KeyError):
            adapter.get_case("nonexistent-case-id")

    def test_iteration(self, mock_hf_dataset) -> None:
        """Can iterate over case IDs."""
        adapter = CaseAdapter(mock_hf_dataset)

        case_ids = list(adapter)

        assert len(case_ids) == len(adapter)
```

#### 4. `tests/data/test_loader.py` - Loader with network mocks

```python
"""Tests for data loader module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.exceptions import DataLoadError
from stroke_deepisles_demo.data.loader import (
    DatasetInfo,
    get_dataset_info,
    load_isles_dataset,
)


class TestLoadIslesDataset:
    """Tests for load_isles_dataset."""

    def test_calls_hf_load_dataset(self) -> None:
        """Calls datasets.load_dataset with correct arguments."""
        with patch("stroke_deepisles_demo.data.loader.load_dataset") as mock_load:
            mock_load.return_value = MagicMock()

            load_isles_dataset("test/dataset")

            mock_load.assert_called_once()
            call_args = mock_load.call_args
            assert call_args.args[0] == "test/dataset"

    def test_returns_dataset_object(self) -> None:
        """Returns the loaded Dataset object."""
        with patch("stroke_deepisles_demo.data.loader.load_dataset") as mock_load:
            expected = MagicMock()
            mock_load.return_value = expected

            result = load_isles_dataset()

            assert result is expected

    def test_handles_load_error(self) -> None:
        """Wraps HF errors in DataLoadError."""
        with patch("stroke_deepisles_demo.data.loader.load_dataset") as mock_load:
            mock_load.side_effect = Exception("Network error")

            with pytest.raises(DataLoadError, match="Network error"):
                load_isles_dataset()


class TestGetDatasetInfo:
    """Tests for get_dataset_info."""

    def test_returns_datasetinfo(self) -> None:
        """Returns DatasetInfo with expected fields."""
        with patch("stroke_deepisles_demo.data.loader.load_dataset") as mock_load:
            mock_ds = MagicMock()
            mock_ds.__len__ = MagicMock(return_value=149)
            mock_ds.features = {"dwi": ..., "adc": ..., "mask": ...}
            mock_load.return_value = mock_ds

            info = get_dataset_info()

            assert isinstance(info, DatasetInfo)
            assert info.num_cases == 149


@pytest.mark.integration
class TestLoadIslesDatasetIntegration:
    """Integration tests that hit the real HuggingFace Hub."""

    @pytest.mark.slow
    def test_load_real_dataset(self) -> None:
        """Actually loads ISLES24-MR-Lite from HF Hub."""
        # This test requires network access
        # Run with: pytest -m integration
        dataset = load_isles_dataset(streaming=True)

        # Just verify we got something
        assert dataset is not None
```

### what to mock

- `datasets.load_dataset` - Mock for unit tests, real for integration tests
- `huggingface_hub` calls - Mock for unit tests
- File system operations - Use `temp_dir` fixture with real files

### what to test for real

- NIfTI file creation/reading with nibabel
- File staging (copy/symlink operations)
- Integration test: actual HF Hub download (marked `@pytest.mark.integration`)

## "done" criteria

Phase 1 is complete when:

1. All unit tests pass: `uv run pytest tests/data/ -v`
2. Can load synthetic test cases without network
3. Can list case IDs from mock dataset
4. Can stage files with correct DeepISLES naming
5. Integration test passes (with network): `uv run pytest -m integration`
6. Type checking passes: `uv run mypy src/stroke_deepisles_demo/data/`
7. Code coverage for data module > 80%

## implementation notes

- ISLES24-MR-Lite structure needs investigation - check HF page for exact column names
- Consider using `huggingface_hub.snapshot_download` if `datasets.load_dataset` has issues with NIfTI
- Staging can use symlinks on Unix, copies on Windows
- Cache the HF dataset locally to avoid repeated downloads

### critical: streaming mode + docker materialization

**Reviewer feedback (valid)**: When using `streaming=True`, the dataset returns URLs or lazy file objects, NOT local POSIX paths. Docker requires physical files on the host disk for volume mounting.

**Solution**: The `stage_case_for_deepisles` function MUST handle materialization:

```python
def stage_case_for_deepisles(
    case_files: CaseFiles,
    output_dir: Path,
    *,
    case_id: str | None = None,
) -> StagedCase:
    """
    Stage case files with DeepISLES-expected naming.

    IMPORTANT: This function handles both local paths and streaming data.
    When files come from streaming mode, they must be downloaded/materialized
    before Docker can mount them.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Handle DWI - may be Path, URL, or NIfTI object
    dwi_staged = output_dir / "dwi.nii.gz"
    _materialize_nifti(case_files["dwi"], dwi_staged)

    # Handle ADC
    adc_staged = output_dir / "adc.nii.gz"
    _materialize_nifti(case_files["adc"], adc_staged)

    # ... etc


def _materialize_nifti(source: Path | str | bytes | NiftiImage, dest: Path) -> None:
    """
    Materialize a NIfTI file to a local path.

    Handles:
    - Local Path: copy or symlink
    - URL string: download
    - bytes: write directly
    - NIfTI object: serialize with nibabel
    """
    if isinstance(source, Path) and source.exists():
        # Local file - symlink if possible, copy otherwise
        shutil.copy2(source, dest)
    elif isinstance(source, str) and source.startswith(("http://", "https://")):
        # URL - download
        _download_file(source, dest)
    elif isinstance(source, bytes):
        # Raw bytes
        dest.write_bytes(source)
    elif hasattr(source, "to_bytes"):
        # NIfTI object (nibabel or wrapper)
        dest.write_bytes(source.to_bytes())
    else:
        raise MissingInputError(f"Cannot materialize source: {type(source)}")
```

This ensures Docker always gets physical files regardless of how data was loaded.

## dependencies to add

No new dependencies needed - all specified in Phase 0:
- `datasets` (Tobias fork)
- `nibabel`
- `numpy`
