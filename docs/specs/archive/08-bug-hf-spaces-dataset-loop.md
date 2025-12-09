# Bug Spec: HuggingFace Spaces Dataset Loading Issues

**Status:** Root Causes Identified → Comprehensive Fix Ready
**Priority:** P0 (Blocks deployment)
**Branch:** `fix/pipeline-resource-leak`
**Date:** 2025-12-08
**Updated:** 2025-12-08

## Executive Summary

Two distinct bugs prevent the HuggingFace Spaces deployment from working:

| Bug | Symptom | Root Cause | Impact | Fix |
|-----|---------|------------|--------|-----|
| **#1** | Dropdown never populates | PyArrow streaming bug | App hangs at startup | Pre-computed case IDs |
| **#2** | OOM on case selection | `load_dataset()` downloads 99GB | App crashes on first use | HfFileSystem + pyarrow |

Both bugs stem from fundamental incompatibilities between the `datasets` library and our 99GB parquet dataset on resource-constrained HF Spaces hardware.

---

## Bug #1: Streaming Iteration Hang

### Summary

The dropdown never populates because `load_dataset(..., streaming=True)` hangs indefinitely on parquet datasets. This is a **known PyArrow bug**, not a HuggingFace datasets bug.

### The Bug Chain

1. **Our code** calls `load_dataset("hugging-science/isles24-stroke", streaming=True)`
2. **HF datasets** internally uses `ParquetFileFragment.to_batches()` for streaming
3. **PyArrow** hangs when iterating batches from parquet with partial consumption
4. **Result:** Script hangs forever, never returns case IDs

### Upstream Issues

- **PyArrow Issue:** [apache/arrow#45214](https://github.com/apache/arrow/issues/45214) - Root cause
- **HF Datasets Issue:** [huggingface/datasets#7467](https://github.com/huggingface/datasets/issues/7467) - HF tracking
- **Status:** Open, no fix ETA
- **Maintainer:** @lhoestq (HF datasets core dev) correctly escalated to PyArrow team

### Minimal Reproduction (Pure PyArrow, no HF)

```python
import pyarrow.dataset as ds

file = "test-00000-of-00003.parquet"
with open(file, "rb") as f:
    parquet_fragment = ds.ParquetFileFormat().make_fragment(f)
    for record_batch in parquet_fragment.to_batches():
        print(len(record_batch))
        break  # ← Partial consumption causes hang
# Script hangs here forever
```

This proves the bug is in **PyArrow's C++ layer**, not HuggingFace datasets.

### Fix: Pre-computed Case ID List

**Why this is professional, not hacky:**

1. **ISLES24 is a static challenge dataset** - case IDs will never change
2. **Industry standard** - many production ML systems pre-define dataset indices
3. **Zero startup latency** - dropdown populates instantly
4. **No network dependency** - works offline for dropdown population
5. **Bypasses upstream bug** - doesn't depend on PyArrow fix timeline

---

## Bug #2: Full Dataset OOM on Case Access

### Summary

Even after fixing Bug #1, the application would crash immediately upon selecting a case. The current `get_case()` implementation calls:

```python
# adapter.py:213
self._hf_dataset = load_dataset(self.dataset_id, split="train")
```

This attempts to download the **entire 99GB dataset** into memory, which OOMs on HF Spaces.

### Why This Wasn't Caught

The bug document initially focused on the dropdown hang (Bug #1). Bug #2 would only manifest after Bug #1 was fixed and a user actually selected a case.

### Investigation Results

| Approach | Result | Time | Memory |
|----------|--------|------|--------|
| `load_dataset(..., streaming=True)` | **HANGS** | ∞ | N/A |
| `load_dataset(...)` (full download) | **OOMs** | ~10 min | 99GB+ |
| `HfFileSystem` + `pyarrow` (single file) | **WORKS** | 1.7s | ~50MB |

### Dataset Structure Discovery

Critical finding: Each case is stored in a **separate parquet file**:

- **149 parquet files** named `train-00000-of-00149.parquet` through `train-00148-of-00149.parquet`
- **Each file = one case** (~600-700MB raw data per case)
- **Schema:** `subject_id`, `dwi`, `adc`, `lesion_mask` (NIfTI bytes stored as binary)

This means we can **directly access individual cases** without loading the full dataset!

### Fix: Direct Parquet Access via HfFileSystem

```python
from huggingface_hub import HfFileSystem
import pyarrow.parquet as pq

fs = HfFileSystem()
fpath = f"datasets/{dataset_id}/data/train-{idx:05d}-of-00149.parquet"

with fs.open(fpath, 'rb') as f:
    pf = pq.ParquetFile(f)
    table = pf.read(columns=['subject_id', 'dwi', 'adc', 'lesion_mask'])
    # Extract ~50MB for one case in ~2 seconds
```

**Benefits:**
- Downloads only the single case needed (~50MB vs 99GB)
- Completes in 1.7 seconds (vs hanging or OOM)
- No dependency on `datasets` library for data access
- Bypasses both PyArrow streaming bug and memory constraints

---

## Comprehensive Fix Implementation

### 1. Create `constants.py` with case ID → file index mapping

```python
# src/stroke_deepisles_demo/data/constants.py

# Pre-computed case IDs for ISLES24 dataset (static challenge dataset)
# Extracted via HfFileSystem enumeration on 2025-12-08
ISLES24_CASE_IDS: tuple[str, ...] = (
    "sub-stroke0001", "sub-stroke0002", ..., "sub-stroke0189"
)

# Mapping from case ID to parquet file index (0-indexed)
ISLES24_CASE_INDEX: dict[str, int] = {
    case_id: idx for idx, case_id in enumerate(ISLES24_CASE_IDS)
}
```

### 2. Rewrite `HuggingFaceDataset.get_case()` to use HfFileSystem

Replace `load_dataset()` call with direct parquet access:

```python
def get_case(self, case_id: str | int) -> CaseFiles:
    from huggingface_hub import HfFileSystem
    import pyarrow.parquet as pq

    idx = self._case_index[case_id]
    fpath = f"datasets/{self.dataset_id}/data/train-{idx:05d}-of-00149.parquet"

    fs = HfFileSystem()
    with fs.open(fpath, 'rb') as f:
        table = pq.ParquetFile(f).read(columns=['dwi', 'adc', 'lesion_mask'])
        # Extract bytes and write to temp files...
```

### 3. Remove all `load_dataset()` calls from HuggingFace path

The `datasets` library is completely bypassed for the HuggingFace workflow.

---

## All 149 Case IDs (Extracted via HfFileSystem)

```
sub-stroke0001, sub-stroke0002, sub-stroke0003, sub-stroke0004, sub-stroke0005,
sub-stroke0006, sub-stroke0007, sub-stroke0008, sub-stroke0009, sub-stroke0010,
sub-stroke0011, sub-stroke0012, sub-stroke0013, sub-stroke0014, sub-stroke0015,
sub-stroke0016, sub-stroke0017, sub-stroke0019, sub-stroke0020, sub-stroke0021,
sub-stroke0022, sub-stroke0025, sub-stroke0026, sub-stroke0027, sub-stroke0028,
sub-stroke0030, sub-stroke0033, sub-stroke0036, sub-stroke0037, sub-stroke0038,
sub-stroke0040, sub-stroke0043, sub-stroke0045, sub-stroke0047, sub-stroke0048,
sub-stroke0049, sub-stroke0052, sub-stroke0053, sub-stroke0054, sub-stroke0055,
sub-stroke0057, sub-stroke0062, sub-stroke0066, sub-stroke0068, sub-stroke0070,
sub-stroke0071, sub-stroke0073, sub-stroke0074, sub-stroke0075, sub-stroke0076,
sub-stroke0077, sub-stroke0078, sub-stroke0079, sub-stroke0080, sub-stroke0081,
sub-stroke0082, sub-stroke0083, sub-stroke0084, sub-stroke0085, sub-stroke0086,
sub-stroke0087, sub-stroke0088, sub-stroke0089, sub-stroke0090, sub-stroke0091,
sub-stroke0092, sub-stroke0093, sub-stroke0094, sub-stroke0095, sub-stroke0096,
sub-stroke0097, sub-stroke0098, sub-stroke0099, sub-stroke0100, sub-stroke0101,
sub-stroke0102, sub-stroke0103, sub-stroke0104, sub-stroke0105, sub-stroke0106,
sub-stroke0107, sub-stroke0108, sub-stroke0109, sub-stroke0110, sub-stroke0111,
sub-stroke0112, sub-stroke0113, sub-stroke0114, sub-stroke0115, sub-stroke0116,
sub-stroke0117, sub-stroke0118, sub-stroke0119, sub-stroke0133, sub-stroke0134,
sub-stroke0135, sub-stroke0136, sub-stroke0137, sub-stroke0138, sub-stroke0139,
sub-stroke0140, sub-stroke0141, sub-stroke0142, sub-stroke0143, sub-stroke0144,
sub-stroke0145, sub-stroke0146, sub-stroke0147, sub-stroke0148, sub-stroke0149,
sub-stroke0150, sub-stroke0151, sub-stroke0152, sub-stroke0153, sub-stroke0154,
sub-stroke0155, sub-stroke0156, sub-stroke0157, sub-stroke0158, sub-stroke0159,
sub-stroke0161, sub-stroke0162, sub-stroke0163, sub-stroke0164, sub-stroke0165,
sub-stroke0166, sub-stroke0167, sub-stroke0168, sub-stroke0169, sub-stroke0170,
sub-stroke0171, sub-stroke0172, sub-stroke0173, sub-stroke0174, sub-stroke0175,
sub-stroke0176, sub-stroke0177, sub-stroke0178, sub-stroke0179, sub-stroke0180,
sub-stroke0181, sub-stroke0182, sub-stroke0183, sub-stroke0184, sub-stroke0185,
sub-stroke0186, sub-stroke0187, sub-stroke0188, sub-stroke0189
```

---

## Environment

- **Space:** `VibecoderMcSwaggins/stroke-deepisles-demo`
- **Hardware:** T4-small GPU (limited memory)
- **Dataset:** `hugging-science/isles24-stroke` (149 parquet files, ~99GB total)
- **Dependencies:**
  - `datasets @ git+https://github.com/CloseChoice/datasets.git@c1c15aa...` (fork with Nifti support)
  - `pyarrow` (inherited, contains Bug #1)
  - `huggingface_hub` (used for Bug #2 fix)

---

## References

- [PyArrow Issue #45214](https://github.com/apache/arrow/issues/45214) - Bug #1 root cause
- [PyArrow Issue #43604](https://github.com/apache/arrow/issues/43604) - Related hang issue
- [HF Datasets Issue #7467](https://github.com/huggingface/datasets/issues/7467) - HF tracking issue
- [HF Datasets Issue #7357](https://github.com/huggingface/datasets/issues/7357) - Original report

---

## Checklist

1. [x] Identify Bug #1 root cause (PyArrow streaming hang)
2. [x] Identify Bug #2 root cause (OOM on full download)
3. [x] Extract all 149 case IDs via HfFileSystem
4. [x] Validate direct parquet access works (1.7s per case)
5. [x] Implement pre-computed case ID list (`constants.py`)
6. [x] Rewrite `get_case()` to use HfFileSystem + pyarrow
7. [x] Update tests
8. [ ] Test on HF Spaces
9. [ ] Monitor PyArrow issue for upstream fix
