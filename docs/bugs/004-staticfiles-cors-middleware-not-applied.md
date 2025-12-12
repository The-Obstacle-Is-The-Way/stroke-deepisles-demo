# Bug 004: CORS/CORP Middleware Not Applied to Mounted StaticFiles

**Status**: OPEN
**Date Found**: 2025-12-12
**Severity**: CRITICAL (blocks NiiVue from loading NIfTI files)
**Requires**: Senior Review

---

## Symptoms

1. Frontend loads successfully at `https://vibecodermcswaggins-stroke-viewer-frontend.hf.space`
2. Backend health check responds: `{"status":"healthy"}`
3. Case dropdown populates (GET /api/cases works)
4. Segmentation job runs successfully (39.5s, returns metrics)
5. Results panel shows: Case, Dice Score (0.000), Volume (0.00 mL), Time (39.5s)
6. **NiiVue viewer shows: "Failed to load volume: Failed to fetch"**

![Screenshot showing the error](../assets/niivue-failed-to-fetch-screenshot.png)

## Root Cause Analysis

### The Core Issue: Starlette Middleware Architecture

When FastAPI/Starlette mounts a sub-application (like `StaticFiles`), the parent app's middleware **does NOT propagate** to the mounted app.

```python
# main.py - Current implementation
app = FastAPI(...)

# These middlewares only apply to routes on `app` itself
app.add_middleware(CORPMiddleware)  # For SharedArrayBuffer
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, ...)

# This creates a SEPARATE sub-application with its OWN middleware stack (empty!)
app.mount("/files", StaticFiles(directory=str(RESULTS_DIR)), name="files")
```

**Result**:
- API routes (`/api/*`) → Get CORS headers ✓
- Static files (`/files/*`) → NO CORS headers ✗ (blocked by browser)

### Evidence

1. Backend logs show all requests succeed with 200 OK
2. Browser DevTools Network tab would show CORS preflight failure for `/files/*` requests
3. NiiVue's `loadVolumes()` throws "Failed to fetch" (generic browser CORS error)

### Starlette Documentation Reference

From [Starlette Middleware Docs](https://www.starlette.io/middleware/):
> "Each sub-app owns its routers/middleware/lifecycle"

From [FastAPI/Starlette Discussion #7319](https://github.com/fastapi/fastapi/discussions/7319):
> "When using `app.mount()`, middleware on the parent app may not apply to mounted sub-apps"

## Impact

- **NiiVue cannot load NIfTI files** - Core functionality completely broken
- **SharedArrayBuffer may not work** - CORP header also missing from static files
- **All production users affected** - Cross-origin fetch blocked

## Proposed Solutions

### Solution A: Custom Route Instead of StaticFiles (Recommended)

Replace `StaticFiles` mount with explicit route handlers that go through the main app's middleware:

```python
from fastapi.responses import FileResponse

@router.get("/files/{job_id}/{case_id}/{filename}")
async def get_result_file(job_id: str, case_id: str, filename: str):
    """Serve NIfTI result files through main app (gets CORS headers)."""
    file_path = RESULTS_DIR / job_id / case_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path,
        media_type="application/gzip",  # .nii.gz
        filename=filename,
    )
```

**Pros**: Simple, uses existing middleware
**Cons**: Less efficient than StaticFiles for large files (no sendfile)

### Solution B: ASGI Middleware Wrapper for StaticFiles

Wrap `StaticFiles` in a custom ASGI app that adds CORS headers:

```python
class CORSStaticFiles:
    """StaticFiles wrapper that adds CORS headers."""

    def __init__(self, directory: str, origins: list[str]):
        self.static = StaticFiles(directory=directory)
        self.origins = origins

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add CORS headers to response
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    origin = dict(scope.get("headers", [])).get(b"origin", b"").decode()
                    if origin in self.origins:
                        headers[b"access-control-allow-origin"] = origin.encode()
                        headers[b"cross-origin-resource-policy"] = b"cross-origin"
                    message["headers"] = list(headers.items())
                await send(message)
            return await self.static(scope, receive, send_with_cors)
        return await self.static(scope, receive, send)

# Usage
app.mount("/files", CORSStaticFiles(str(RESULTS_DIR), CORS_ORIGINS))
```

**Pros**: Preserves StaticFiles efficiency
**Cons**: More complex, custom ASGI code

### Solution C: Nginx/Caddy Reverse Proxy

Add CORS headers at the reverse proxy level (HF Spaces would need configuration access):

**Pros**: Most efficient, proper separation of concerns
**Cons**: HF Spaces may not support custom proxy config

## Additional Issues Discovered

### Issue 1: BACKEND_PUBLIC_URL Not Set

The Dockerfile doesn't set `BACKEND_PUBLIC_URL`, relying on `--proxy-headers` and `request.base_url`. This is fragile:

```dockerfile
# Current (fragile)
CMD ["uvicorn", "...:app", "--proxy-headers"]

# Should add (robust)
ENV BACKEND_PUBLIC_URL=https://vibecodermcswaggins-stroke-deepisles-demo.hf.space
```

### Issue 2: chmod "Operation not permitted" Warnings

```
chmod: changing permissions of '/app/weights/SEALS/nnUNet_trained_models/...': Operation not permitted
```

**Status**: Harmless - DeepISLES tries to chmod model weights but fails. The container can still READ the files, which is all that's needed. These are benign warnings, not errors.

## Files Affected

- `src/stroke_deepisles_demo/api/main.py` - Needs fix for static file CORS
- `Dockerfile` - Should set `BACKEND_PUBLIC_URL` explicitly

## Verification Steps

After fix:
1. Deploy updated backend to HF Spaces
2. Clear browser cache
3. Open frontend, select case, run segmentation
4. Check browser DevTools → Network tab:
   - `/files/*` requests should show `access-control-allow-origin` header
5. NiiVue should load and display DWI + prediction overlay

## References

- [FastAPI/Starlette CORS Discussion #7319](https://github.com/fastapi/fastapi/discussions/7319)
- [Starlette Middleware Stack](https://www.starlette.io/middleware/)
- [FastAPI CORS Tutorial](https://fastapi.tiangolo.com/tutorial/cors/)
- [CORSMiddleware not working with mounted apps](https://github.com/fastapi/fastapi/issues/1663)

## Senior Review Questions

1. **Solution preference**: Route-based (A) vs ASGI wrapper (B)?
2. **BACKEND_PUBLIC_URL**: Set in Dockerfile or HF Space settings?
3. **Testing**: Add integration test for static file CORS headers?
4. **Monitoring**: How to detect this regression in future?
