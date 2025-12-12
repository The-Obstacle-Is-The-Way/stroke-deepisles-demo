# Bug Tracker: HuggingFace Spaces Deployment

This directory tracks bugs found during deployment to HuggingFace Spaces.

## Active Bugs

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| [004](./004-staticfiles-cors-middleware-not-applied.md) | CORS/CORP middleware not applied to mounted StaticFiles | **CRITICAL** | OPEN - Awaiting Senior Review |

## Fixed Bugs

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| [001](./001-cors-static-files-hf-spaces.md) | CORS regex blocking static file requests | Critical | FIXED |
| [002](./002-http-vs-https-proxy-headers.md) | HTTP vs HTTPS URL mismatch behind proxy | High | FIXED |
| [003](./003-gateway-timeout-long-inference.md) | Gateway timeout for long ML inference | Medium | FIXED |

## HF Spaces Deployment Checklist

Last audit: 2025-12-12

| Check | Status | Notes |
|-------|--------|-------|
| CORS regex matches both URL formats | N/A | Replaced with exact-match list (PR #38) |
| **CORS on StaticFiles mount** | **FAIL** | BUG-004: Middleware doesn't apply to mounted apps |
| All URLs use HTTPS | PASS | `--proxy-headers` flag in Dockerfile |
| File outputs to /tmp/ | PASS | Uses `/tmp/stroke-results/` |
| Static files mounted after dir exists | PASS | `mkdir()` before `app.mount()` in main.py |
| HF_SPACES env var set | PASS | Set in Dockerfile |
| Using port 7860 | PASS | Configured in Dockerfile CMD |
| Inference timeout handled | PASS | Async job queue pattern (no timeout risk) |
| Error responses return JSON | PASS | HTTPException with detail |
| CORS preflight (OPTIONS) handled | PASS | CORSMiddleware handles automatically |
| Progress updates for long tasks | PASS | Polling with ProgressIndicator component |

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

### 6. chmod "Operation not permitted" Warnings (HARMLESS)
DeepISLES tries to chmod model weight files but fails due to container permissions:
```
chmod: changing permissions of '/app/weights/SEALS/...': Operation not permitted
```
These are **benign warnings**, not errors. The container can still READ the files.

### 7. Gateway Timeouts (SOLVED)
- HF Spaces proxy has ~60 second timeout
- Solution: Async job queue pattern with polling
- POST returns immediately with job ID
- Frontend polls GET /api/jobs/{id} for progress
- See [Bug 003](./003-gateway-timeout-long-inference.md) and [Spec](../specs/async-job-queue.md)

## E2E Flow (v2.0 - Async Job Pattern)

The complete flow from frontend to backend and back:

```text
1. Frontend loads
   ├── CaseSelector fetches GET /api/cases
   ├── CORS: origin regex must match frontend URL
   └── Response: JSON list of case IDs

2. User runs segmentation
   ├── App calls POST /api/segment {case_id, fast_mode}
   ├── Backend creates job record
   └── Response: 202 Accepted + {jobId, status: "pending"}

3. Frontend polls for status
   ├── GET /api/jobs/{jobId} every 2 seconds
   ├── Response: {status, progress, progressMessage}
   └── ProgressIndicator shows real-time updates

4. Backend processes (in background thread)
   ├── Job status: "running"
   ├── Progress updates: 10% → 30% → 85% → 95%
   ├── Runs DeepISLES inference
   └── Writes results to /tmp/stroke-results/{jobId}/

5. Job completes
   ├── Status: "completed"
   ├── Result includes file URLs
   └── Frontend stops polling

6. Frontend receives result
   ├── Updates state with URLs
   ├── Passes URLs to NiiVueViewer
   └── Shows metrics in MetricsPanel

7. NiiVue fetches static files
   ├── Cross-origin fetch to backend /files/...
   ├── ⚠️ BUG-004: StaticFiles mount doesn't get CORS headers!
   ├── Browser blocks fetch (no Access-Control-Allow-Origin)
   └── "Failed to load volume: Failed to fetch"

8. Viewer displays
   └── NIfTI volumes rendered in WebGL canvas
```

## API Endpoints (v2.0)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/cases | List available cases |
| POST | /api/segment | Create segmentation job (202 Accepted) |
| GET | /api/jobs/{id} | Get job status/progress/results |
| GET | /files/{jobId}/{caseId}/* | Static NIfTI files |
| GET | / | Health check |
| GET | /health | Detailed health with job count |

## Sources

- [Deploying FastAPI on HuggingFace Spaces](https://huggingface.co/blog/HemanthSai7/deploy-applications-on-huggingface-spaces)
- [HF Spaces Restrictions](https://medium.com/@na.mazaheri/deploying-a-fastapi-app-on-hugging-face-spaces-and-handling-all-its-restrictions-d494d97a78fa)
- [FastAPI HTTPS Discussion](https://github.com/fastapi/fastapi/discussions/6670)
- [HF Docker Spaces Docs](https://huggingface.co/docs/hub/en/spaces-sdks-docker)
- [504 Gateway Timeout - HF Forums](https://discuss.huggingface.co/t/504-gateway-timeout-with-http-request/24018)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI Polling Strategy](https://openillumi.com/en/en-fastapi-long-task-progress-polling/)
