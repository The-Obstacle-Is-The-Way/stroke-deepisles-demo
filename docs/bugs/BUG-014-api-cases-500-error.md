# BUG-014: /api/cases Returns 500 Internal Server Error

**Status**: INVESTIGATING
**Severity**: P1 (Frontend completely broken)
**Discovered**: 2025-12-15
**Reporter**: Manual testing

## Symptoms

1. Frontend shows "Loading cases..." indefinitely
2. Backend health check returns 200 OK with healthy status
3. GET `/api/cases` returns HTTP 500 Internal Server Error

## Evidence

### Backend Health (Working)
```
https://vibecodermcswaggins-stroke-deepisles-demo.hf.space/
```
Returns:
```json
{"status":"healthy","service":"stroke-segmentation-api","version":"2.0.0","features":["async-jobs","progress-tracking"]}
```

### Cases Endpoint (Failing)
```
https://vibecodermcswaggins-stroke-deepisles-demo.hf.space/api/cases
```
Returns: HTTP 500 Internal Server Error

## Root Cause Analysis

### Call Chain
```
GET /api/cases
  → routes.py:get_cases()
    → data/__init__.py:list_case_ids()
      → data/loader.py:load_isles_dataset()
        → datasets.load_dataset("hugging-science/isles24-stroke", ...)
```

### Dataset Status
- **Dataset**: `hugging-science/isles24-stroke`
- **Access**: PUBLIC (no authentication required)
- **License**: CC BY-NC-SA 4.0

### Potential Causes (In Order of Likelihood)

1. ~~**Missing `datasets` Library**~~ **RULED OUT**
   - `neuroimaging-go-brrrr` depends on `datasets>=3.4.0`
   - HOWEVER: Uses custom uv source pinning to a git commit (not PyPI)
   - This addresses an "embed_table_storage bug" - may still cause issues

2. **neuroimaging-go-brrrr Installation Failure**
   - Installed from git: `git+https://github.com/.../neuroimaging-go-brrrr.git@v0.2.1`
   - Git installs in Docker can fail silently if network issues
   - Package provides Nifti feature for datasets library

3. **Memory/Storage Constraints**
   - HF Spaces T4-small has limited RAM
   - Loading dataset indices may exceed memory
   - `/tmp` storage may be exhausted

4. **Network Issue**
   - HF Spaces backend can't reach HF Hub
   - DNS resolution failure
   - SSL certificate issue

## Reproduction

### Local Test
```bash
uv sync --extra api
uv run python -c "from stroke_deepisles_demo.data import list_case_ids; print(list_case_ids())"
```

### HF Space Logs
Check HF Space logs for the actual exception:
1. Go to https://huggingface.co/spaces/VibecoderMcSwaggins/stroke-deepisles-demo
2. Click "Logs" tab
3. Look for Python traceback when `/api/cases` is called

## Impact

- Frontend is completely non-functional
- Users cannot select cases or run segmentation
- Backend health check gives false confidence

## Recommended Investigation Steps

1. **Check HF Space Logs**
   - View actual Python exception traceback
   - Identify if ImportError, MemoryError, or other

2. **Verify Dependencies in Container**
   ```bash
   # SSH into space or add debug endpoint
   pip list | grep -E "datasets|neuroimaging"
   ```

3. **Test Dataset Loading Directly**
   - Add temporary debug endpoint to verify load_dataset works
   - Or check if `datasets` import succeeds in lifespan handler

4. **Check for Missing Dependency**
   - If `datasets` is missing, add to pyproject.toml dependencies
   - Rebuild and redeploy

## Related Files

- `src/stroke_deepisles_demo/api/routes.py:49-63` - get_cases endpoint
- `src/stroke_deepisles_demo/data/__init__.py:34-44` - list_case_ids function
- `src/stroke_deepisles_demo/data/loader.py:157-227` - load_isles_dataset function
- `pyproject.toml` - dependencies (missing `datasets`?)

## Immediate Next Step

**CHECK THE HF SPACE LOGS** - this is the only way to confirm the actual exception.

1. Go to: https://huggingface.co/spaces/VibecoderMcSwaggins/stroke-deepisles-demo
2. Click "Logs" tab (or burger menu → "Logs")
3. Look for Python traceback
4. The exception will tell us exactly what's failing

## Notes

- This bug was NOT caused by the frontend Static SDK deployment fix
- The backend has been returning 500 on `/api/cases` - we just didn't notice until now
- Need HF Space logs to confirm root cause before fixing
- Do NOT deploy fixes until root cause is confirmed from logs
