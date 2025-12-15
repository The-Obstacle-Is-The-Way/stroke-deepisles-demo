# BUG-014: /api/cases Endpoint Timeout

**Status**: ROOT CAUSE CONFIRMED, FIX IDENTIFIED
**Severity**: P1 (Frontend completely broken)
**Discovered**: 2025-12-15
**Reporter**: Manual testing

## Summary

The `/api/cases` endpoint failed on HF Spaces because it triggered an eager ~27GB
dataset download/prepare step just to return a list of case IDs.

The fix keeps the *full* dataset, but changes the data access pattern so:
- `/api/cases` does **zero** dataset downloading
- `get_case(case_id)` downloads **one** Parquet shard (one case), not the full dataset

## Root Cause

**Current code path:**
```text
GET /api/cases
  → routes.py:57           list_case_ids()
    → data/__init__.py:43    load_isles_dataset()
      → loader.py:224        ds = load_dataset(...)  ← DOWNLOADS 27GB EAGERLY
```

**The bug:** `datasets.load_dataset(dataset_id, split="train")` downloads/prepares the full
dataset on cold start. On HF Spaces this regularly exceeds the proxy timeout window, so
the frontend never receives a usable case list.

## Previous Misdiagnosis

This was identified in `ARCHITECTURE-AUDIT-2024-12-13.md` as P2-006 and dismissed in `REMAINING-ISSUES-2024-12-13.md`:

> "Dataset reload per request | ACCEPTABLE | Demo scale (149 cases), adds negligible latency"

**This assessment was wrong.** The latency isn't from "149 cases"—it's from an eager
27GB download/prepare step happening in the request path.

## Verified Facts

| Fact | Value | Verification |
|------|-------|--------------|
| Total download | 27.41 GB | `load_dataset_builder().info.download_size` |
| Number of cases | 149 | `info.splits['train'].num_examples` |
| Shards | 149 parquet files | HF Hub API |
| Shard shape | 1 case per parquet file | `load_dataset(..., data_files={...})` returns 1 row |
| Case ID range | `sub-stroke0001` … `sub-stroke0189` (with gaps) | subject_id per shard |

## The Fix

### Part 1: Instant Case List (No Download)

**Problem:** `list_case_ids()` was implemented by loading the dataset, which on HF Spaces
meant triggering the full 27GB download/prepare.

**Solution:** Use a pinned manifest of case IDs for the ISLES24 dataset.

Implemented at `src/stroke_deepisles_demo/data/isles24_manifest.py` (pinned to dataset revision).

### Part 2: Per-Case Loading by Shard (No Full Download)

**Problem:** `get_case(case_id)` previously loaded the whole dataset, even when only one
case is needed for inference.

**Solution:** For a single case, load exactly one Parquet shard using `data_files=...`,
then materialize DWI/ADC (and optional lesion mask) to temp files.

Implemented in `src/stroke_deepisles_demo/data/loader.py` as `Isles24HuggingFaceDataset`.

### Why This Works on HF Spaces

- `/api/cases` becomes a pure metadata response (fast, reliable).
- Per-case data download happens in the background job (fits the async job model).
- No streaming iteration over the full dataset is required.

## Files to Change

| File | Change |
|------|--------|
| `src/stroke_deepisles_demo/data/isles24_manifest.py` | Add pinned case ID manifest + shard mapping |
| `src/stroke_deepisles_demo/data/loader.py` | Add `Isles24HuggingFaceDataset` + route ISLES24 loads to it |

## Implementation Steps

1. Add pinned ISLES24 case ID manifest (no download on `/api/cases`)
2. Load single Parquet shard via `data_files=...` for `get_case(case_id)`
3. Verify `/api/cases` returns immediately on HF Spaces
4. Verify segmentation job downloads only selected case data

## Verification After Fix

```bash
# After deploying fix, from cold start:
time curl -s https://vibecodermcswaggins-stroke-deepisles-demo.hf.space/api/cases
# Should complete quickly with {"cases": ["sub-stroke0001", ...]}
```

## Notes

- The full 27GB dataset IS supported - we're not reducing it
- Case loading happens in background jobs, not blocking the API gateway timeout window
- The core issue was doing full-dataset work inside `/api/cases`
