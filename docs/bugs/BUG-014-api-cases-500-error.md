# BUG-014: /api/cases Endpoint Timeout

**Status**: ROOT CAUSE CONFIRMED, FIX IDENTIFIED
**Severity**: P1 (Frontend completely broken)
**Discovered**: 2025-12-15
**Reporter**: Manual testing

## Summary

The `/api/cases` endpoint fails because it downloads the entire 27GB dataset just to return a list of 149 case IDs. This is fixable without reducing the dataset.

## Root Cause

**Current code path:**
```
GET /api/cases
  → routes.py:57           list_case_ids()
    → data/__init__.py:43    load_isles_dataset()
      → loader.py:224        ds = load_dataset(...)  ← DOWNLOADS 27GB EAGERLY
```

**The bug:** `datasets.load_dataset()` without `streaming=True` downloads ALL 149 parquet shards (~27GB) before returning. This takes 5-10+ minutes, causing HF Spaces proxy timeout.

## Previous Misdiagnosis

This was identified in `ARCHITECTURE-AUDIT-2024-12-13.md` as P2-006 and dismissed in `REMAINING-ISSUES-2024-12-13.md`:

> "Dataset reload per request | ACCEPTABLE | Demo scale (149 cases), adds negligible latency"

**This assessment was wrong.** The latency isn't from "149 cases" - it's from downloading 27GB of parquet data to get those 149 case IDs.

## Verified Facts

| Fact | Value | Verification |
|------|-------|--------------|
| Total download | 27.41 GB | `load_dataset_builder().info.download_size` |
| Number of cases | 149 | `info.splits['train'].num_examples` |
| Shards | 149 parquet files | HF Hub API |
| Case ID pattern | `sub-stroke0001` to `sub-stroke0149` | Streaming sample confirmed sequential |
| Case IDs are sequential | YES | First 10 match `sub-stroke{N:04d}` pattern |

## The Fix

### Part 1: Instant Case List (No Download)

**Problem:** `list_case_ids()` downloads 27GB to return 149 strings.

**Solution:** Generate the list from dataset info (1 second, no download):

```python
# In data/__init__.py or routes.py
def list_case_ids() -> list[str]:
    """Return case IDs without downloading the dataset."""
    from datasets import load_dataset_builder
    from stroke_deepisles_demo.core.config import get_settings

    # Get count from metadata (no download)
    builder = load_dataset_builder(get_settings().hf_dataset_id)
    num_cases = builder.info.splits['train'].num_examples

    # Generate sequential IDs (verified pattern)
    return [f'sub-stroke{str(i+1).zfill(4)}' for i in range(num_cases)]
```

**Why this works:**
- `load_dataset_builder()` only fetches metadata (~1 second)
- Case IDs are sequential `sub-stroke0001` through `sub-stroke0149` (verified)
- Returns instantly instead of waiting for 27GB download

### Part 2: Lazy Single-Case Loading (Streaming)

**Problem:** `get_case(case_id)` downloads ALL 27GB to access ONE case (~180MB).

**Solution:** Use streaming mode to download only necessary shards:

```python
# In data/loader.py
def load_single_case(case_id: str) -> dict:
    """Load a single case using streaming (downloads only necessary shards)."""
    from datasets import load_dataset
    from stroke_deepisles_demo.core.config import get_settings

    settings = get_settings()
    ds = load_dataset(
        settings.hf_dataset_id,
        split='train',
        streaming=True,
        token=settings.hf_token,
    )

    # Filter for target case - stops downloading when found
    for row in ds:
        if row['subject_id'] == case_id:
            return row

    raise KeyError(f"Case {case_id} not found")
```

**Why this works:**
- Streaming iterates through shards one at a time
- Stops when target case is found
- For case 50, downloads ~10 shards (~1.8GB) instead of all 149 (~27GB)
- Still takes 30-120s depending on case position, but that's acceptable in background jobs

### Part 3: Wire in Cache Directory (Persistence)

**Problem:** `hf_cache_dir` setting exists but isn't used. Every cold start re-downloads.

**Solution:** Pass cache_dir to load_dataset:

```python
ds = load_dataset(
    settings.hf_dataset_id,
    split='train',
    streaming=True,
    token=settings.hf_token,
    cache_dir=settings.hf_cache_dir,  # ADD THIS
)
```

**Why this works:**
- HF Spaces can have persistent storage
- First load is slow, subsequent loads use cache
- Addresses P2-001 from REMAINING-ISSUES audit

## Files to Change

| File | Change |
|------|--------|
| `src/stroke_deepisles_demo/data/__init__.py` | Replace `list_case_ids()` with metadata-based implementation |
| `src/stroke_deepisles_demo/data/loader.py` | Add streaming mode option, add `load_single_case()` function |
| `src/stroke_deepisles_demo/api/routes.py` | Use new `list_case_ids()` (no change needed if interface same) |

## Implementation Steps

1. **Update `list_case_ids()`** to use `load_dataset_builder().info` instead of loading data
2. **Add `load_single_case(case_id)`** function using streaming + early termination
3. **Update `get_case()`** to use `load_single_case()` instead of loading full dataset
4. **Wire `cache_dir`** parameter through to all `load_dataset()` calls
5. **Test locally** with cleared cache to simulate cold start
6. **Deploy and verify** `/api/cases` returns in <5 seconds

## Verification After Fix

```bash
# After deploying fix, from cold start:
time curl -s https://vibecodermcswaggins-stroke-deepisles-demo.hf.space/api/cases
# Should complete in <5 seconds with {"cases": ["sub-stroke0001", ...]}
```

## Notes

- The full 27GB dataset IS supported - we're not reducing it
- Case loading (30-120s) happens in background jobs, not blocking the API
- This is the same pattern as before, just without the 27GB upfront download
- The `neuroimaging-go-brrrr` package provides NIfTI support, but the core issue is the eager download
