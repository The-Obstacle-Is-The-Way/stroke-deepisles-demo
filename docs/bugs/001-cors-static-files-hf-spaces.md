# Bug 001: CORS Blocking Static File Requests on HuggingFace Spaces

**Status**: FIXED
**Date Found**: 2025-12-11
**Severity**: Critical (blocks core functionality)

---

## Symptoms

1. Frontend loads successfully, case dropdown populates
2. Segmentation API call succeeds (200 OK, ~34s processing time)
3. Results panel shows metrics (Dice Score, Volume, Time)
4. NiiVue viewer shows "loading..." then error: **"Failed to load volume: Failed to fetch"**

## Root Cause

The CORS `allow_origin_regex` pattern in `src/stroke_deepisles_demo/api/main.py` was incorrect:

```python
# WRONG - expects double hyphens
allow_origin_regex=r"https://.*--stroke-viewer-frontend(--.*)?\.hf\.space"

# Actual frontend URL uses single hyphen:
# https://vibecodermcswaggins-stroke-viewer-frontend.hf.space
#                           ^ single hyphen
```

The regex expected `--` (double hyphen) between username and space name, but HuggingFace Spaces direct URLs use single hyphens.

## HuggingFace Spaces URL Formats

| Format | Pattern | Example |
|--------|---------|---------|
| **Direct** | `{username}-{spacename}.hf.space` | `vibecodermcswaggins-stroke-viewer-frontend.hf.space` |
| **Proxy/Embed** | `{username}--{spacename}--{hash}.hf.space` | `vibecodermcswaggins--stroke-viewer-frontend--abc123.hf.space` |

The original regex only matched the proxy format, not the direct format.

## Fix

```python
# CORRECT - matches both formats
allow_origin_regex=r"https://.*stroke-viewer-frontend.*\.hf\.space"
```

## Logs Evidence

```
INFO: 10.16.13.79:42834 - "POST /api/segment HTTP/1.1" 200 OK
```

The API call succeeded, but subsequent static file fetches for NIfTI volumes were blocked by CORS (browser silently blocks and shows "Failed to fetch").

## Files Changed

- `src/stroke_deepisles_demo/api/main.py` - Fixed regex
- `docs/specs/frontend/36-frontend-without-gradio-hf-spaces.md` - Updated spec

## Verification

After fix:
1. Redeploy backend to HF Spaces
2. Refresh frontend
3. Run segmentation
4. NiiVue should load and display the DWI + prediction overlay

## Prevention

- Test CORS configuration with actual production URLs before deployment
- Add integration test that verifies static file CORS headers
- Document HF Spaces URL formats in spec
