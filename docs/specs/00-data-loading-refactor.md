# SPEC-00: Data Loading Refactor

> **Status:** Draft (Updated per Senior Review)
> **Priority:** Critical
> **Estimated Scope:** Delete ~350 lines, add ~100 lines, rewrite 2 test files

---

## Problem Statement

`stroke-deepisles-demo` has a hand-rolled data loading workaround that:

1. **Bypasses `datasets.load_dataset()`** - Uses `HfFileSystem + pyarrow` directly
2. **Duplicates bug workarounds** - Should live in `neuroimaging-go-brrrr`
3. **Doesn't use `Nifti()` feature type** - Manually extracts bytes from parquet
4. **Pre-computes 149 case IDs** - Static list that could drift from source

This defeats the purpose of depending on `neuroimaging-go-brrrr`.

---

## Root Cause

The workaround was created due to:
- PyArrow streaming bug (apache/arrow#45214) - hangs on parquet iteration
- Memory concerns about downloading 99GB

**But:** These should be solved in `neuroimaging-go-brrrr`, not locally.

---

## Current Architecture (WRONG)

```text
stroke-deepisles-demo
        │
        ├── data/adapter.py (379 lines)
        │   ├── HuggingFaceDataset class
        │   │   ├── _download_case_from_parquet() - manual parquet reading
        │   │   └── Uses HfFileSystem + pyarrow directly
        │   └── build_huggingface_dataset() - bypasses load_dataset()
        │
        ├── data/constants.py (182 lines)
        │   └── ISLES24_CASE_IDS - pre-computed 149 case IDs
        │
        ├── data/loader.py
        │   └── load_isles_dataset() - dispatches to adapter
        │
        └── tests/data/
            ├── test_hf_adapter.py - tests HuggingFaceDataset (DELETE/REWRITE)
            └── test_loader.py - imports HuggingFaceDataset (UPDATE)
```

---

## What Nifti() Actually Returns

**CRITICAL CORRECTION:** The original spec incorrectly stated `Nifti()` returns numpy arrays.

Per the `datasets` source code:
- **`Nifti(decode=True)`** (default): Returns a `Nifti1ImageWrapper` (subclass of `nibabel.nifti1.Nifti1Image`)
  - The wrapper calls `get_fdata()` in its constructor (eager load to RAM)
  - Preserves affine and header
- **`Nifti(decode=False)`**: Returns a dict `{"path": ..., "bytes": ...}`

This means:
```python
ds = load_dataset("hugging-science/isles24-stroke", split="train")
example = ds[0]
dwi = example["dwi"]  # nibabel.Nifti1Image, NOT numpy array
```

---

## CaseFiles Contract

The existing `CaseFiles` TypedDict expects **Paths**, not nibabel images:

```python
# core/types.py:12
class CaseFiles(TypedDict):
    dwi: Path
    adc: Path
    flair: NotRequired[Path]
    ground_truth: NotRequired[Path]
```

Downstream code (`pipeline.py:124`) uses:
```python
shutil.copy2(case_files["dwi"], dwi_dest)  # Expects Path!
```

**The new wrapper MUST continue materializing to temp files to preserve this contract.**

---

## Target Architecture (CORRECT)

```text
stroke-deepisles-demo
        │
        └── data/loader.py
            └── load_isles_dataset()
                │
                │  from datasets import load_dataset
                │  ds = load_dataset("hugging-science/isles24-stroke")
                ▼
        HuggingFaceDatasetWrapper (thin wrapper)
                │
                │  get_case() materializes nibabel → temp file → Path
                ▼
        CaseFiles (Paths to temp files, same contract as before)
```

---

## Files to Modify

### DELETE

| File | Lines | Reason |
|------|-------|--------|
| `data/constants.py` | 182 | Pre-computed IDs no longer needed |
| `data/adapter.py` (partial) | ~250 | `HuggingFaceDataset` class + `build_huggingface_dataset()` |

**Keep in `adapter.py`:**
- `LocalDataset` class (for local BIDS directories)
- `build_local_dataset()` function
- `parse_subject_id()` helper

### DELETE/REWRITE (Tests)

| File | Reason |
|------|--------|
| `tests/data/test_hf_adapter.py` | Tests deleted `HuggingFaceDataset` class |
| `tests/data/test_loader.py` | Imports `HuggingFaceDataset` |

### MODIFY

| File | Change |
|------|--------|
| `data/loader.py` | Add `HuggingFaceDatasetWrapper`, use `load_dataset()` |
| `data/__init__.py` | Update exports |

### NO CHANGE NEEDED

| File | Reason |
|------|--------|
| `data/staging.py` | Already handles nibabel via `hasattr(source, "to_filename")` |
| `pipeline.py` | Will work unchanged if wrapper returns Paths |

---

## Implementation Plan

### Phase 1: Add HuggingFaceDatasetWrapper

```python
# data/loader.py

from pathlib import Path
import tempfile
import shutil

class HuggingFaceDatasetWrapper:
    """Thin wrapper matching Dataset protocol.

    Uses datasets.load_dataset() for consumption.
    Materializes nibabel images to temp files to preserve CaseFiles contract.
    """

    def __init__(self, hf_dataset, dataset_id: str):
        self._ds = hf_dataset
        self._dataset_id = dataset_id
        self._temp_dir: Path | None = None
        self._cached_cases: dict[str, CaseFiles] = {}
        # Build subject_id index once (avoid repeated iteration)
        self._subject_index: dict[str, int] = {
            row["subject_id"]: i for i, row in enumerate(self._ds)
        }

    def __len__(self) -> int:
        return len(self._ds)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.cleanup()

    def list_case_ids(self) -> list[str]:
        """Return sorted list of subject IDs (uses cached index)."""
        return sorted(self._subject_index.keys())

    def get_case(self, case_id: str | int) -> CaseFiles:
        """Get case - materializes nibabel images to temp files."""
        # Resolve case_id
        if isinstance(case_id, int):
            subject_id = list(self._subject_index.keys())[case_id]
            idx = case_id
        else:
            subject_id = case_id
            idx = self._subject_index[subject_id]

        # Return cached if available
        if subject_id in self._cached_cases:
            return self._cached_cases[subject_id]

        # Create temp dir on first use
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="isles24_hf_"))

        # Get row from dataset (this triggers Nifti() decode)
        row = self._ds[idx]

        # Materialize nibabel images to temp files
        case_dir = self._temp_dir / subject_id
        case_dir.mkdir(exist_ok=True)

        dwi_path = case_dir / f"{subject_id}_dwi.nii.gz"
        adc_path = case_dir / f"{subject_id}_adc.nii.gz"

        # row["dwi"] is a nibabel.Nifti1Image
        row["dwi"].to_filename(str(dwi_path))
        row["adc"].to_filename(str(adc_path))

        case_files: CaseFiles = {
            "dwi": dwi_path,
            "adc": adc_path,
        }

        # Handle lesion_mask if present
        if row.get("lesion_mask") is not None:
            mask_path = case_dir / f"{subject_id}_lesion-msk.nii.gz"
            row["lesion_mask"].to_filename(str(mask_path))
            case_files["ground_truth"] = mask_path

        self._cached_cases[subject_id] = case_files
        return case_files

    def cleanup(self) -> None:
        """Remove temp directory."""
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)
        self._temp_dir = None
        self._cached_cases.clear()
```

### Phase 2: Update load_isles_dataset()

```python
def load_isles_dataset(
    source: str | Path | None = None,
    *,
    local_mode: bool | None = None,
) -> Dataset:
    """Load ISLES24 dataset."""

    if local_mode:
        from stroke_deepisles_demo.data.adapter import build_local_dataset
        return build_local_dataset(Path(source or "data/isles24"))

    # HuggingFace mode - USE STANDARD CONSUMPTION
    from datasets import load_dataset

    dataset_id = str(source) if source else "hugging-science/isles24-stroke"
    ds = load_dataset(dataset_id, split="train")

    return HuggingFaceDatasetWrapper(ds, dataset_id)
```

### Phase 3: Delete Dead Code

1. Delete `data/constants.py` entirely
2. Remove from `adapter.py`:
   - `HuggingFaceDataset` class (lines 143-337)
   - `build_huggingface_dataset()` function (lines 339-378)
3. Delete `tests/data/test_hf_adapter.py`
4. Rewrite `tests/data/test_loader.py` to not import deleted classes

### Phase 4: Test

1. Verify `load_isles_dataset()` works with HuggingFace
2. Verify nibabel → temp file materialization works
3. Verify `pipeline.py` still works (shutil.copy2 on Paths)
4. Run inference end-to-end

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Full dataset download** | HIGH | `load_dataset()` may download all 27GB. Test if streaming or column selection works. May need to file issue in neuroimaging-go-brrrr. |
| **All modalities decoded** | MEDIUM | Accessing `ds[i]` may decode ALL Nifti columns (ncct, cta, ctp, tmax...). Consider `ds.select_columns(["subject_id", "dwi", "adc", "lesion_mask"])` |
| **Eager RAM load** | MEDIUM | `Nifti1ImageWrapper` calls `get_fdata()` in constructor. For large 4D volumes this could be GB per modality. |
| **Byte-for-byte fidelity** | LOW | `to_filename()` may re-encode differently than original bytes. Verify inference results are equivalent. |
| **O(n) index build** | LOW | Building `_subject_index` iterates full dataset once. Acceptable for 149 rows. |

---

## Performance Considerations

The current adapter downloads ~50MB per case on-demand. The new approach may:
1. Download more data upfront (all parquet shards)
2. Decode more modalities than needed

**If this regresses performance significantly:**
1. File issue in `neuroimaging-go-brrrr` for selective loading
2. Consider `streaming=True` mode (if supported with Nifti)
3. Consider column selection before access

---

## Success Criteria

1. `data/constants.py` deleted
2. `HuggingFaceDataset` class deleted
3. `load_isles_dataset()` uses `datasets.load_dataset()`
4. All tests pass (with rewritten HF tests)
5. Inference works end-to-end
6. No regression in single-case load time (verify <30s)

---

## Dependencies

- `neuroimaging-go-brrrr @ v0.2.1` (already installed)
- Patched `datasets` with `Nifti()` support (provided by neuroimaging-go-brrrr)

---

## Open Questions (To Validate During Implementation)

1. Does `load_dataset()` download all shards or lazy-load?
2. Does `ds.select_columns()` prevent unwanted Nifti decodes?
3. Is `streaming=True` compatible with `Nifti()` features?
4. Any byte-for-byte differences when re-encoding via nibabel?

These should be answered by testing, not by adding local workarounds.
