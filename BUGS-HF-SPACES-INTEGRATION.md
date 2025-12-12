# Bug Report: HuggingFace Spaces Frontend/Backend Integration

**Date**: 2025-12-12
**Auditor**: Claude Code
**Status**: Pre-deployment audit (UPDATED after URL verification)

---

## Executive Summary

Audit of the frontend/backend integration for HuggingFace Spaces deployment. After verifying against the **actual deployed Space URLs**, the core configuration is **CORRECT**. No P0/P1 blockers found. Minor P2/P3 improvements identified.

### Actual Space URLs (Verified)
- **Frontend**: https://huggingface.co/spaces/VibecoderMcSwaggins/stroke-viewer-frontend
  - Runtime URL: `https://vibecodermcswaggins-stroke-viewer-frontend.hf.space`
- **Backend**: https://huggingface.co/spaces/VibecoderMcSwaggins/stroke-deepisles-demo
  - Runtime URL: `https://vibecodermcswaggins-stroke-deepisles-demo.hf.space`

---

## Configuration Verification (All PASS)

| Component | Configuration | Status | Evidence |
|-----------|--------------|--------|----------|
| CORS Regex | `r"https://.*stroke-viewer-frontend.*\.hf\.space"` | **PASS** | Matches `vibecodermcswaggins-stroke-viewer-frontend.hf.space` |
| Backend URL in Frontend | `VITE_API_URL=https://vibecodermcswaggins-stroke-deepisles-demo.hf.space` | **PASS** | Correctly points to backend |
| Built dist has production URL | `https://vibecodermcswaggins-stroke-deepisles-demo.hf.space` | **PASS** | Verified in `dist/assets/index-*.js` |
| Proxy headers | `--proxy-headers` in Dockerfile CMD | **PASS** | Ensures HTTPS URLs behind HF proxy |
| Port configuration | 7860 | **PASS** | Matches HF Spaces requirements |
| Results directory | `/tmp/stroke-results` | **PASS** | Writable on HF Spaces |
| Async job queue | Implemented | **PASS** | Avoids 60s gateway timeout |

### CORS Regex Verification

```python
# Test performed:
import re
frontend_url = 'https://vibecodermcswaggins-stroke-viewer-frontend.hf.space'
cors_regex = r'https://.*stroke-viewer-frontend.*\.hf\.space'
re.fullmatch(cors_regex, frontend_url)  # Returns Match object - SUCCESS

# Also matches proxy/embed format:
proxy_url = 'https://vibecodermcswaggins--stroke-viewer-frontend--abc123.hf.space'
re.fullmatch(cors_regex, proxy_url)  # Returns Match object - SUCCESS
```

---

## P2 - MEDIUM PRIORITY (Non-blocking)

### ISSUE-001: Hardcoded User in Production Config

**Severity**: P2 - MEDIUM
**Impact**: Forks/clones require manual configuration update
**Files**: `frontend/.env.production`, `frontend/dist/`

#### Problem

The production URL is hardcoded for a specific user:
```
# frontend/.env.production
VITE_API_URL=https://vibecodermcswaggins-stroke-deepisles-demo.hf.space
```

Anyone forking this repo must:
1. Update `.env.production` with their backend URL
2. Rebuild the frontend (`npm run build`)
3. Re-deploy the dist folder

#### Recommendation (Optional)

Add a deployment note to `frontend/README.md`:
```markdown
## Fork Deployment

If you fork this repo, update `.env.production` before building:
\`\`\`
VITE_API_URL=https://{YOUR_USERNAME}-stroke-deepisles-demo.hf.space
\`\`\`
Then rebuild: `npm run build`
```

---

### ISSUE-002: allow_credentials May Be Unnecessary

**Severity**: P2 - MEDIUM
**Impact**: More permissive than needed
**File**: `src/stroke_deepisles_demo/api/main.py:87`

#### Problem

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*stroke-viewer-frontend.*\.hf\.space",
    allow_credentials=True,  # <-- Is this needed?
    allow_methods=["*"],
    allow_headers=["*"],
)
```

The frontend API client doesn't use credentials:
```typescript
// frontend/src/api/client.ts - no credentials option in fetch calls
const response = await fetch(`${this.baseUrl}/api/cases`, { signal })
```

#### Recommendation (Optional)

If credentials (cookies, auth headers) aren't needed, consider:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*stroke-viewer-frontend.*\.hf\.space",
    allow_credentials=False,  # More restrictive
    allow_methods=["GET", "POST"],  # Only methods actually used
    allow_headers=["Content-Type"],  # Only headers actually needed
)
```

This follows the principle of least privilege.

---

## P3 - LOW PRIORITY (Nice-to-have)

### ISSUE-003: FRONTEND_ORIGIN Env Var Not Used

**Severity**: P3 - LOW
**Impact**: Works without it, but could be more explicit
**File**: `Dockerfile`, `src/stroke_deepisles_demo/api/main.py:72-78`

#### Problem

The code supports `FRONTEND_ORIGIN` environment variable:
```python
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "")
if FRONTEND_ORIGIN:
    CORS_ORIGINS.append(FRONTEND_ORIGIN)
```

But it's not set in the Dockerfile. The regex fallback works, but explicit is better than implicit.

#### Recommendation (Optional)

Add to Dockerfile:
```dockerfile
ENV FRONTEND_ORIGIN=https://vibecodermcswaggins-stroke-viewer-frontend.hf.space
```

Or document that users can set it as a Space secret for more explicit configuration.

---

## P4 - INFO (No Action Required)

### INFO-001: Static Space README Configuration

**Status**: CORRECT
**File**: `frontend/README.md`

The Static Space header is properly configured:
```yaml
---
title: Stroke Lesion Viewer
emoji: 🧠
sdk: static
app_file: dist/index.html
app_build_command: npm run build
nodejs_version: "20"  # Required for Vite 7
---
```

### INFO-002: Backend Dockerfile Configuration

**Status**: CORRECT
**File**: `Dockerfile`

All critical settings are present:
- `FROM isleschallenge/deepisles:latest` - Correct base image
- `USER user` - Non-root user (required by HF Spaces)
- `EXPOSE 7860` - Correct port
- `--proxy-headers` - Trusts X-Forwarded-Proto

### INFO-003: Async Job Queue Pattern

**Status**: CORRECT
**Files**: `src/stroke_deepisles_demo/api/routes.py`, `frontend/src/hooks/useSegmentation.ts`

The implementation correctly handles HF Spaces' ~60s gateway timeout:
1. POST `/api/segment` returns immediately with job ID (202 Accepted)
2. Frontend polls GET `/api/jobs/{id}` every 2 seconds
3. Progress updates shown via `ProgressIndicator`

---

## Pre-Deployment Checklist

Before going live, verify these items:

| Check | Status | Notes |
|-------|--------|-------|
| Frontend Space created | [ ] | `stroke-viewer-frontend` Static Space |
| Backend Space created | [ ] | `stroke-deepisles-demo` Docker Space |
| Backend Space has GPU | [ ] | T4 or better required for DeepISLES |
| Frontend built with production env | [x] | dist/ contains correct backend URL |
| CORS regex matches frontend URL | [x] | Verified via regex test |
| `--proxy-headers` in Dockerfile | [x] | Ensures HTTPS URLs |
| Port 7860 configured | [x] | Required by HF Spaces |
| Results dir in /tmp | [x] | `/tmp/stroke-results` |

---

## Runtime Testing Checklist

Once both Spaces are running:

| Test | Expected Result | How to Verify |
|------|-----------------|---------------|
| Frontend loads | Page renders without errors | Open frontend URL in browser |
| Backend health check | `{"status": "healthy", ...}` | `curl https://...-stroke-deepisles-demo.hf.space/health` |
| Cases endpoint | JSON array of case IDs | Check Network tab in DevTools |
| CORS on cases | No CORS error | Check Console tab in DevTools |
| Segmentation job created | 202 response with jobId | Click "Run Segmentation" |
| Progress polling | Progress updates in UI | Watch ProgressIndicator |
| Results displayed | NiiVue viewer shows volumes | Verify 3D rendering |
| Static file CORS | NIfTI files load without error | Check Network tab |

---

## Previously Fixed Issues (Reference)

These issues from earlier audits are correctly resolved:

| ID | Issue | Fix Applied |
|----|-------|-------------|
| 001 | CORS regex only matched proxy URL format | Fixed: `.*stroke-viewer-frontend.*` matches both |
| 002 | HTTP URLs returned behind HTTPS proxy | Fixed: `--proxy-headers` in uvicorn CMD |
| 003 | Gateway timeout on long inference | Fixed: Async job queue with polling |

---

## Sources

- [HuggingFace Static Spaces](https://huggingface.co/docs/hub/en/spaces-sdks-static)
- [HF Spaces URL Format](https://huggingface.co/docs/hub/spaces-embed)
- [FastAPI CORS Configuration](https://www.stackhawk.com/blog/configuring-cors-in-fastapi/)
- [Deploying FastAPI on HF Spaces](https://huggingface.co/blog/HemanthSai7/deploy-applications-on-huggingface-spaces)
- [HF Spaces Docker Docs](https://huggingface.co/docs/hub/spaces-sdks-docker)
