# BUG-014: /api/cases Endpoint Timeout/500 Error

**Status**: ROOT CAUSE CONFIRMED
**Severity**: P1 (Frontend completely broken)
**Discovered**: 2025-12-15
**Reporter**: Manual testing

## Summary

The `/api/cases` endpoint fails because it triggers a full 27GB dataset download on every request. This is an architectural design flaw, not a missing dependency or configuration issue.

## Verified Call Chain

```
GET /api/cases
  → routes.py:57        list_case_ids()
    → data/__init__.py:43  load_isles_dataset(source=source)
      → loader.py:224      ds = load_dataset(dataset_id, split="train", token=hf_token)
                           ↑ DOWNLOADS ENTIRE 27GB DATASET
```

## Root Cause (Confirmed)

**The `datasets.load_dataset()` call at `loader.py:224` downloads the entire dataset.**

Dataset facts (verified via HF Hub API):
- **Dataset ID**: `hugging-science/isles24-stroke`
- **Size**: 149 parquet shards × ~184MB average = **~27.41GB total**
- **Access**: PUBLIC (no auth required)
- **Smallest shard**: 95.82MB
- **Largest shard**: 260.09MB

When `/api/cases` is called:
1. `list_case_ids()` calls `load_isles_dataset()`
2. `load_isles_dataset()` calls HuggingFace's `load_dataset()`
3. `load_dataset()` downloads ALL 149 parquet shards (~27GB)
4. This takes 5-10+ minutes on HF Spaces network
5. HF Spaces proxy timeout (60-120s) kills the request
6. Frontend sees timeout or 500 error

## Evidence

| Test | Result |
|------|--------|
| `GET /` (health) | 200 OK in ~143s after cold start |
| `GET /health` | 200 OK in ~286s after cold start |
| `GET /api/cases` | Timeout after 300s (curl max-time) |
| CORS headers | Present and correct |
| Dataset public? | Yes, no token required |

The health endpoints work because they don't touch the dataset. The `/api/cases` endpoint fails because it's the first endpoint that triggers `load_isles_dataset()`.

## Why HF Space Logs Won't Help

The logs show:
```
INFO: Application startup complete.
INFO: 10.16.9.169:20572 - "GET /health HTTP/1.1" 200 OK
```

We don't see `/api/cases` logged because:
1. Uvicorn logs requests AFTER response is sent
2. The request never completes (times out at proxy)
3. No Python exception is raised (still downloading)

We have enough information - logs would only confirm what we already know.

## Why This Passed Local Testing

Local development likely used:
1. Cached dataset from previous runs
2. Faster local disk I/O
3. No HF Spaces proxy timeout
4. Different network conditions

## Architectural Flaw

The design assumes `datasets.load_dataset()` is fast/cached. On HF Spaces:
- Cold starts have empty cache
- `/tmp` storage is limited and ephemeral
- Downloading 27GB for a simple case list is not viable

## Fix Options

### Option A: Use a Small Demo Dataset (Recommended)
Create a curated HF dataset with 5-10 representative cases (~500MB).
- Fastest to implement
- Reliable for demos
- Clear scope

### Option B: Streaming Mode
Use `datasets.load_dataset(..., streaming=True)` to avoid full download.
- Requires refactoring `HuggingFaceDatasetWrapper`
- May still have performance issues for random case access

### Option C: Direct HF Hub API
Call HF Hub API directly to get case list from metadata without downloading data.
```python
from huggingface_hub import HfApi
api = HfApi()
# Get dataset info without downloading
info = api.dataset_info("hugging-science/isles24-stroke")
```
- More complex implementation
- Decouples metadata from data access

### Option D: Pre-computed Case List
Hardcode or cache the case ID list, load individual cases on demand.
- Simple but requires knowing case IDs in advance
- Doesn't scale if dataset changes

## Recommendation

**Option A (small demo dataset)** is the cleanest fix for a demo application. The 27GB medical imaging dataset is production-scale data that shouldn't be loaded on every API request.

## Files Requiring Changes

| File | Change |
|------|--------|
| `src/stroke_deepisles_demo/core/config.py` | Update `hf_dataset_id` default |
| `pyproject.toml` | No changes needed |
| New HF Dataset | Create `VibecoderMcSwaggins/isles24-demo` with 5-10 cases |

## Verification Steps After Fix

```bash
# 1. Deploy updated backend to HF Spaces
# 2. Wait for cold start to complete
# 3. Test:
curl -s https://vibecodermcswaggins-stroke-deepisles-demo.hf.space/api/cases
# Should return {"cases": ["sub-stroke0001", ...]} within 5-10 seconds
```

## Notes

- This bug was always present but masked by local caching
- Frontend fix (Static SDK deployment) exposed the backend issue
- The 500 error is actually a timeout converted to error by HF proxy
- No code changes were made to cause this - it's a deployment environment difference
