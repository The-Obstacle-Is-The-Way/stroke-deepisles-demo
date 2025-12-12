# Bug Tracker: HuggingFace Spaces Deployment

This directory tracks bugs found during deployment to HuggingFace Spaces.

## Active Bugs

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| [003](./003-gateway-timeout-long-inference.md) | Gateway timeout risk for long ML inference | Medium | DOCUMENTED |

## Fixed Bugs

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| [001](./001-cors-static-files-hf-spaces.md) | CORS regex blocking static file requests | Critical | FIXED |
| [002](./002-http-vs-https-proxy-headers.md) | HTTP vs HTTPS URL mismatch behind proxy | High | FIXED |

## HF Spaces Deployment Checklist

Last audit: 2025-12-12

| Check | Status | Notes |
|-------|--------|-------|
| CORS regex matches both URL formats | PASS | `r"https://.*stroke-viewer-frontend.*\.hf\.space"` |
| All URLs use HTTPS | PASS | `--proxy-headers` flag in Dockerfile |
| File outputs to /tmp/ | PASS | Uses `/tmp/stroke-results/` |
| Static files mounted after dir exists | PASS | `mkdir()` before `app.mount()` in main.py |
| HF_SPACES env var set | PASS | Set in Dockerfile |
| Using port 7860 | PASS | Configured in Dockerfile CMD |
| Inference timeout < 60s | WARN | 30-60s typical, HF proxy ~60s limit |
| Error responses return JSON | PASS | HTTPException with detail |
| CORS preflight (OPTIONS) handled | PASS | CORSMiddleware handles automatically |

## Common HuggingFace Spaces Pitfalls

Based on research and experience, here are common issues to watch for:

### 1. CORS Configuration
- HF Spaces URLs use single hyphens: `{username}-{spacename}.hf.space`
- Proxy/embed URLs may use double hyphens: `{username}--{spacename}--{hash}.hf.space`
- Always use a permissive regex that matches both formats

### 2. HTTPS Behind Proxy
- HF Spaces terminates SSL at their proxy
- Uvicorn sees HTTP internally
- Add `--proxy-headers` to trust `X-Forwarded-Proto`
- Or explicitly set `BACKEND_PUBLIC_URL` environment variable

### 3. File System Restrictions
- Only `/tmp` is writable
- Use `/tmp/stroke-results` for output files
- Ensure directories are created with proper permissions

### 4. Static Files
- Mount static files AFTER directory exists
- Ensure CORS allows file fetches from frontend origin
- Files served from `/files/...` must be accessible

### 5. Environment Variables
- `HF_SPACES=1` indicates running on HF Spaces
- `SPACE_ID` contains the space identifier
- Use these to detect production environment

### 6. Gateway Timeouts (NEW)
- HF Spaces proxy has ~60 second timeout
- Long-running ML inference may exceed this limit
- Consider async/polling patterns for >30s operations
- See [Bug 003](./003-gateway-timeout-long-inference.md) for details

## E2E Flow Audit

The complete flow from frontend to backend and back:

```
1. Frontend loads
   ├── CaseSelector fetches GET /api/cases
   ├── CORS: origin regex must match frontend URL
   └── Response: JSON list of case IDs

2. User runs segmentation
   ├── App calls POST /api/segment {case_id, fast_mode}
   ├── CORS: preflight OPTIONS handled by middleware
   └── Backend: sync endpoint runs in threadpool

3. Backend processes
   ├── Generates unique run_id (UUID[:8])
   ├── Runs DeepISLES inference (30-60s)
   ├── Writes results to /tmp/stroke-results/{run_id}/
   └── WARNING: May timeout if >60s

4. Backend returns response
   ├── Constructs URLs using get_backend_base_url()
   ├── --proxy-headers ensures https:// prefix
   └── Response: JSON with dwiUrl, predictionUrl, metrics

5. Frontend receives response
   ├── Updates state with result URLs
   ├── Passes URLs to NiiVueViewer
   └── Error handling for 504/network errors

6. NiiVue fetches static files
   ├── Cross-origin fetch to backend /files/...
   ├── CORS headers required on static file response
   ├── Content-Type: application/gzip for .nii.gz
   └── Binary transfer must complete successfully

7. Viewer displays
   └── NIfTI volumes rendered in WebGL canvas
```

## Sources

- [Deploying FastAPI on HuggingFace Spaces](https://huggingface.co/blog/HemanthSai7/deploy-applications-on-huggingface-spaces)
- [HF Spaces Restrictions](https://medium.com/@na.mazaheri/deploying-a-fastapi-app-on-hugging-face-spaces-and-handling-all-its-restrictions-d494d97a78fa)
- [FastAPI HTTPS Discussion](https://github.com/fastapi/fastapi/discussions/6670)
- [HF Docker Spaces Docs](https://huggingface.co/docs/hub/en/spaces-sdks-docker)
- [504 Gateway Timeout - HF Forums](https://discuss.huggingface.co/t/504-gateway-timeout-with-http-request/24018)
- [CORS Issue with HF Spaces - HF Forums](https://discuss.huggingface.co/t/cors-issue-with-huggingface-spaces-and-netlify-hosted-react-app/62634)
