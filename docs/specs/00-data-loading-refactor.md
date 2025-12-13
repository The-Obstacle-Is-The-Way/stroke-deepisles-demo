# SPEC-00: Data Loading Refactor

> **Status:** Draft
> **Priority:** Critical
> **Estimated Scope:** Delete ~350 lines, add ~50 lines

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

```
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
        └── data/loader.py
            └── load_isles_dataset() - dispatches to adapter
```

---

## Target Architecture (CORRECT)

```
stroke-deepisles-demo
        │
        └── data/loader.py
            └── load_isles_dataset()
                │
                │  from datasets import load_dataset
                │  ds = load_dataset("hugging-science/isles24-stroke")
                ▼
        neuroimaging-go-brrrr (patched datasets with Nifti())
                │
                │  Nifti() feature type handles everything
                ▼
        HuggingFace Hub
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

### MODIFY

| File | Change |
|------|--------|
| `data/loader.py` | Use `datasets.load_dataset()` for HF mode |
| `data/__init__.py` | Update exports |
| `data/staging.py` | May need to handle `Nifti()` lazy-loaded arrays |

---

## Implementation Plan

### Phase 1: Refactor `loader.py`

Replace HuggingFace mode with standard consumption:

```python
# data/loader.py

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

    dataset_id = source if source else "hugging-science/isles24-stroke"
    ds = load_dataset(dataset_id, split="train")

    return HuggingFaceDatasetWrapper(ds)


class HuggingFaceDatasetWrapper:
    """Thin wrapper to match Dataset protocol."""

    def __init__(self, hf_dataset):
        self._ds = hf_dataset

    def __len__(self) -> int:
        return len(self._ds)

    def list_case_ids(self) -> list[str]:
        return [row["subject_id"] for row in self._ds]

    def get_case(self, case_id: str | int) -> CaseFiles:
        """Get case - Nifti() handles lazy loading automatically."""
        if isinstance(case_id, int):
            row = self._ds[case_id]
        else:
            # Find by subject_id
            idx = next(i for i, r in enumerate(self._ds) if r["subject_id"] == case_id)
            row = self._ds[idx]

        return {
            "dwi": row["dwi"],      # numpy array (lazy loaded)
            "adc": row["adc"],      # numpy array (lazy loaded)
            "ground_truth": row.get("lesion_mask"),
        }
```

### Phase 2: Update `staging.py`

The `_materialize_nifti()` function needs to handle numpy arrays from `Nifti()`:

```python
def _materialize_nifti(source: Path | str | bytes | np.ndarray | Any, dest: Path) -> None:
    """Materialize a NIfTI file to a local path."""

    if isinstance(source, np.ndarray):
        # Nifti() feature returns numpy array
        # Need to create NIfTI with identity affine
        import nibabel as nib
        img = nib.Nifti1Image(source, np.eye(4))
        nib.save(img, dest)
    elif isinstance(source, Path):
        # ... existing code ...
```

### Phase 3: Delete Dead Code

1. Delete `data/constants.py` entirely
2. Remove from `adapter.py`:
   - `HuggingFaceDataset` class (lines 143-337)
   - `build_huggingface_dataset()` function (lines 339-378)
3. Update `data/__init__.py` exports

### Phase 4: Test

1. Verify `load_isles_dataset()` works with HuggingFace
2. Verify `Nifti()` lazy loading works
3. Verify staging materializes numpy arrays correctly
4. Run inference end-to-end

---

## Risks

| Risk | Mitigation |
|------|------------|
| `Nifti()` returns numpy, not file paths | Update `staging.py` to handle numpy arrays |
| Memory usage if full dataset loads | Check if `Nifti()` does true lazy loading |
| Affine/header lost from `Nifti()` | May need to verify DeepISLES doesn't need specific headers |

---

## Success Criteria

1. `data/constants.py` deleted
2. `HuggingFaceDataset` class deleted
3. `load_isles_dataset()` uses `datasets.load_dataset()`
4. All tests pass
5. Inference works end-to-end

---

## Dependencies

- `neuroimaging-go-brrrr @ v0.2.1` (already installed)
- Patched `datasets` with `Nifti()` support (provided by neuroimaging-go-brrrr)

---

## Open Questions

1. Does `Nifti()` return the affine matrix? Or just the data array?
2. If streaming is needed (for 99GB concern), does `load_dataset(..., streaming=True)` work with `Nifti()`?

These should be answered by testing, not by adding local workarounds.
