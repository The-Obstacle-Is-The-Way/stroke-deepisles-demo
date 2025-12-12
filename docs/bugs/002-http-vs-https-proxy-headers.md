# Bug 002: HTTP vs HTTPS URL Mismatch Behind HF Spaces Proxy

**Status**: FIXED
**Date Found**: 2025-12-11
**Severity**: High (may cause mixed content errors or fetch failures)

---

## Symptoms

NiiVue viewer fails to load NIfTI files with "Failed to fetch" even after CORS is fixed.
Browser console may show mixed content warnings (HTTPS page loading HTTP resources).

## Root Cause

HuggingFace Spaces runs containers behind a reverse proxy that handles SSL termination.
When the app constructs URLs using `request.base_url`, it may return `http://` instead of `https://`
because uvicorn doesn't trust the proxy's `X-Forwarded-Proto` header by default.

**Reference**: [FastAPI Static Files over HTTPS Discussion](https://github.com/fastapi/fastapi/discussions/6670)

> "Starlette (FastAPI) returns http instead of https only inside containers"

## The Code Path

```python
# routes.py
def get_backend_base_url(request: Request) -> str:
    env_url = os.environ.get("BACKEND_PUBLIC_URL", "").rstrip("/")
    if env_url:
        return env_url
    return str(request.base_url).rstrip("/")  # May return http:// behind proxy!
```

## Fix

Add `--proxy-headers` flag to uvicorn in Dockerfile:

```dockerfile
# BEFORE (broken)
CMD ["uvicorn", "...:app", "--host", "0.0.0.0", "--port", "7860"]

# AFTER (fixed)
CMD ["uvicorn", "...:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers"]
```

This tells uvicorn to trust headers like:
- `X-Forwarded-Proto: https`
- `X-Forwarded-For: client-ip`

## Alternative Fixes

1. **Set BACKEND_PUBLIC_URL**: Explicitly set the public URL in HF Space settings
   ```
   BACKEND_PUBLIC_URL=https://vibecodermcswaggins-stroke-deepisles-demo.hf.space
   ```

2. **Force HTTPS in code**: Override scheme detection
   ```python
   def get_backend_base_url(request: Request) -> str:
       base = str(request.base_url).rstrip("/")
       # Force HTTPS in production
       if os.environ.get("HF_SPACES"):
           base = base.replace("http://", "https://")
       return base
   ```

## Files Changed

- `Dockerfile` - Added `--proxy-headers` to uvicorn CMD

## Verification

1. Deploy to HF Spaces
2. Run segmentation
3. Check Network tab - file URLs should be `https://`
4. NiiVue should load volumes successfully

## Sources

- [FastAPI/Starlette HTTPS Discussion](https://github.com/fastapi/fastapi/discussions/6670)
- [Deploying FastAPI on HuggingFace Spaces](https://medium.com/@na.mazaheri/deploying-a-fastapi-app-on-hugging-face-spaces-and-handling-all-its-restrictions-d494d97a78fa)
