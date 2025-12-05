# phase 1: data access layer

## purpose

Implement a data loading layer that provides typed access to ISLES24 neuroimaging cases. This phase is split into sub-phases due to a critical discovery: the upstream dataset is not properly formatted for HuggingFace consumption.

## critical discovery (2025-12-04)

**`YongchengYAO/ISLES24-MR-Lite` is NOT a proper HuggingFace Dataset.**

| What we expected | What actually exists |
|------------------|---------------------|
| `load_dataset()` returns Dataset with columns | `load_dataset()` FAILS with "no data" |
| Columns: `dwi`, `adc`, `mask`, `participant_id` | No columns - just raw ZIP files |
| Parquet/Arrow format | Three ZIP archives dumped on HF |

**Evidence**: `data/scratch/isles24_schema_report.txt`

This means the demo must be built in phases:
1. **Phase 1A**: Local file loader (works NOW with extracted data)
2. **Phase 1B**: Test Tobias's `Nifti()` feature on local files (proves loading works)
3. **Phase 1C**: Upload properly to HuggingFace (future - proves production pipeline)
4. **Phase 1D**: Consume via Tobias's fork (future - proves full round-trip)

---

## phase 1a: local file loader (CURRENT PRIORITY)

### data location

```
data/scratch/isles24_extracted/     # Git-ignored
├── Images-DWI/                     # 149 files
│   └── sub-stroke{XXXX}_ses-02_dwi.nii.gz
├── Images-ADC/                     # 149 files
│   └── sub-stroke{XXXX}_ses-02_adc.nii.gz
└── Masks/                          # 149 files
    └── sub-stroke{XXXX}_ses-02_lesion-msk.nii.gz
```

### file naming convention (BIDS-like)

| Component | Pattern | Example |
|-----------|---------|---------|
| Subject ID | `sub-stroke{XXXX}` | `sub-stroke0005` |
| Session | `ses-02` | Always "02" in this dataset |
| Modality | `dwi`, `adc`, `lesion-msk` | - |
| Extension | `.nii.gz` | Compressed NIfTI |

**Subject ID regex**: `sub-stroke(\d{4})_ses-02_.*\.nii\.gz`

**Note**: Subject IDs have gaps (e.g., 0018 missing). Range is 0001-0189, total 149 cases.

### deliverables

- [ ] `src/stroke_deepisles_demo/data/loader.py` - Rewrite with local mode
- [ ] `src/stroke_deepisles_demo/data/adapter.py` - Rewrite for file-based access
- [ ] `src/stroke_deepisles_demo/data/staging.py` - Already correct, no changes
- [ ] Unit tests with synthetic fixtures
- [ ] Integration test with actual extracted data

### interfaces

#### `data/loader.py`

```python
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
    source: str | Path = "data/scratch/isles24_extracted",
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
        DataLoadError: If data cannot be loaded
    """
    if local_mode or isinstance(source, Path):
        return _load_from_local_directory(Path(source))
    # Future: return _load_from_huggingface(source)
    raise NotImplementedError("HuggingFace mode not yet implemented")


def _load_from_local_directory(data_dir: Path) -> LocalDataset:
    """
    Load cases from extracted local files.

    Expects structure:
        data_dir/
        ├── Images-DWI/sub-stroke{XXXX}_ses-02_dwi.nii.gz
        ├── Images-ADC/sub-stroke{XXXX}_ses-02_adc.nii.gz
        └── Masks/sub-stroke{XXXX}_ses-02_lesion-msk.nii.gz
    """
    ...
```

#### `data/adapter.py`

```python
"""Provide typed access to ISLES24 cases."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from stroke_deepisles_demo.core.types import CaseFiles


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
    """
    dwi_dir = data_dir / "Images-DWI"
    adc_dir = data_dir / "Images-ADC"
    mask_dir = data_dir / "Masks"

    cases: dict[str, CaseFiles] = {}

    # Scan DWI files to get subject IDs
    for dwi_file in dwi_dir.glob("*.nii.gz"):
        subject_id = parse_subject_id(dwi_file.name)
        if not subject_id:
            continue

        # Find matching ADC and Mask
        adc_file = adc_dir / dwi_file.name.replace("_dwi.", "_adc.")
        mask_file = mask_dir / dwi_file.name.replace("_dwi.", "_lesion-msk.")

        if not adc_file.exists():
            continue  # Skip incomplete cases

        cases[subject_id] = CaseFiles(
            dwi=dwi_file,
            adc=adc_file,
            ground_truth=mask_file if mask_file.exists() else None,
        )

    return LocalDataset(data_dir=data_dir, cases=cases)
```

### synthetic fixture structure

Unit tests MUST use fixtures that replicate the **exact** directory structure. Add to `tests/conftest.py`:

```python
@pytest.fixture
def synthetic_isles_dir(temp_dir: Path) -> Path:
    """
    Create synthetic ISLES24-like directory structure.

    Structure:
        temp_dir/
        ├── Images-DWI/
        │   ├── sub-stroke0001_ses-02_dwi.nii.gz
        │   └── sub-stroke0002_ses-02_dwi.nii.gz
        ├── Images-ADC/
        │   ├── sub-stroke0001_ses-02_adc.nii.gz
        │   └── sub-stroke0002_ses-02_adc.nii.gz
        └── Masks/
            ├── sub-stroke0001_ses-02_lesion-msk.nii.gz
            └── sub-stroke0002_ses-02_lesion-msk.nii.gz
    """
    dwi_dir = temp_dir / "Images-DWI"
    adc_dir = temp_dir / "Images-ADC"
    mask_dir = temp_dir / "Masks"

    dwi_dir.mkdir()
    adc_dir.mkdir()
    mask_dir.mkdir()

    for subject_num in [1, 2]:
        subject_id = f"sub-stroke{subject_num:04d}"

        # Create DWI
        dwi_data = np.random.rand(10, 10, 5).astype(np.float32)
        dwi_img = nib.Nifti1Image(dwi_data, affine=np.eye(4))
        nib.save(dwi_img, dwi_dir / f"{subject_id}_ses-02_dwi.nii.gz")

        # Create ADC
        adc_data = np.random.rand(10, 10, 5).astype(np.float32) * 2000
        adc_img = nib.Nifti1Image(adc_data, affine=np.eye(4))
        nib.save(adc_img, adc_dir / f"{subject_id}_ses-02_adc.nii.gz")

        # Create Mask
        mask_data = (np.random.rand(10, 10, 5) > 0.9).astype(np.uint8)
        mask_img = nib.Nifti1Image(mask_data, affine=np.eye(4))
        nib.save(mask_img, mask_dir / f"{subject_id}_ses-02_lesion-msk.nii.gz")

    return temp_dir
```

### tdd plan

```python
# tests/data/test_loader.py

def test_load_from_local_returns_local_dataset(synthetic_isles_dir):
    """Local mode returns LocalDataset."""
    ...

def test_load_from_local_finds_all_cases(synthetic_isles_dir):
    """Finds all cases in synthetic structure."""
    ...

# tests/data/test_adapter.py

def test_parse_subject_id_extracts_correctly():
    """Extracts subject ID from BIDS filename."""
    assert parse_subject_id("sub-stroke0005_ses-02_dwi.nii.gz") == "sub-stroke0005"

def test_build_local_dataset_matches_files(synthetic_isles_dir):
    """Matches DWI, ADC, Mask by subject ID."""
    ...

def test_get_case_returns_case_files(synthetic_isles_dir):
    """get_case returns CaseFiles with correct paths."""
    ...
```

### done criteria (phase 1a)

- [ ] `uv run pytest tests/data/ -v` passes
- [ ] Can load all 149 cases from `data/scratch/isles24_extracted/`
- [ ] `list_case_ids()` returns 149 subject IDs
- [ ] `get_case("sub-stroke0005")` returns valid CaseFiles
- [ ] Type checking passes: `uv run mypy src/stroke_deepisles_demo/data/`

---

## phase 1b: test tobias's nifti feature (NEXT)

### purpose

Verify that Tobias's `Nifti()` feature type from the datasets fork can correctly load/parse NIfTI files. This proves the **loading** part of the consumption pipeline works, even though the **download** part is broken.

### approach

```python
# Test script to verify Nifti() feature works on local files
from datasets import Features, Value
from datasets.features import Nifti  # From Tobias's fork

# Create a simple dataset from local files
features = Features({
    "subject_id": Value("string"),
    "dwi": Nifti(),
    "adc": Nifti(),
    "mask": Nifti(),
})

# Load a single case and verify Nifti() decodes correctly
```

### done criteria (phase 1b)

- [ ] Tobias's `Nifti()` feature loads local `.nii.gz` files
- [ ] Decoded NIfTI has correct shape/dtype
- [ ] Can access voxel data via nibabel-like interface

---

## phase 1c: proper huggingface upload (FUTURE)

### purpose

Re-upload ISLES24 data to HuggingFace **properly** using the arc-aphasia-bids approach. This proves the **production** pipeline works.

### approach

1. Use BIDS loader from Tobias's fork
2. Create proper parquet schema with columns:
   - `subject`: string
   - `session`: string
   - `dwi`: Nifti()
   - `adc`: Nifti()
   - `mask`: Nifti()
3. Upload to new HuggingFace repo (e.g., `The-Obstacle-Is-The-Way/ISLES24-BIDS`)

### done criteria (phase 1c)

- [ ] Dataset uploaded to HuggingFace with proper schema
- [ ] HuggingFace dataset viewer shows data correctly
- [ ] `load_dataset("new-repo-id")` returns Dataset with expected columns

---

## phase 1d: consumption verification (FUTURE)

### purpose

Verify the full round-trip: Download from HuggingFace using Tobias's fork.

### approach

```python
from datasets import load_dataset

# This should work after Phase 1C
ds = load_dataset("The-Obstacle-Is-The-Way/ISLES24-BIDS")
case = ds["train"][0]
print(case["dwi"].shape)  # Should work!
```

### new adapter function

When Phase 1D is implemented, `adapter.py` will need a new function alongside `build_local_dataset`:

```python
def adapt_hf_case(hf_row: dict) -> CaseFiles:
    """
    Adapt a HuggingFace Dataset row to CaseFiles.

    Args:
        hf_row: Row from load_dataset() with columns:
            - dwi: Nifti feature (nibabel-like object)
            - adc: Nifti feature
            - mask: Nifti feature
            - subject: str

    Returns:
        CaseFiles with materialized paths or nibabel objects
    """
    # Implementation depends on how Nifti() feature exposes data
    # May need to write to temp files or pass nibabel objects directly
    ...
```

This maintains the same `CaseFiles` contract for downstream phases regardless of data source.

### done criteria (phase 1d)

- [ ] `load_dataset()` works on properly uploaded dataset
- [ ] `adapt_hf_case()` function converts HF rows to CaseFiles
- [ ] Full demo runs with HuggingFace consumption (not just local files)
- [ ] Documents the pitfall for future projects

---

## dependencies

No new dependencies needed beyond Phase 0.

## notes

- The original `adapter.py` assumed HF Dataset with columns - COMPLETELY WRONG
- The original `loader.py` called `load_dataset()` directly - FAILS on this dataset
- `staging.py` is still correct - it just needs `CaseFiles` with paths
