# Bug Report: HuggingFace Spaces Frontend/Backend Integration

**Date**: 2025-12-12
**Auditor**: Claude Code + External Agent Review
**Status**: Pre-deployment audit (v3 - externally validated)

---

## Executive Summary

Comprehensive audit of the frontend/backend integration for HuggingFace Spaces deployment, validated by external senior review. **Core CORS and URL configuration is correct**, but critical operational and security issues were identified that require attention before production use.

### Actual Space URLs (Verified)
- **Frontend**: https://huggingface.co/spaces/VibecoderMcSwaggins/stroke-viewer-frontend
  - Runtime URL: `https://vibecodermcswaggins-stroke-viewer-frontend.hf.space`
- **Backend**: https://huggingface.co/spaces/VibecoderMcSwaggins/stroke-deepisles-demo
  - Runtime URL: `https://vibecodermcswaggins-stroke-deepisles-demo.hf.space`

---

## P1 - HIGH PRIORITY (Operational Blockers)

### BUG-001: No Cold Start / 503 Error Handling

**Severity**: P1 - HIGH
**Impact**: First user request fails when backend Space is sleeping
**File**: `frontend/src/hooks/useSegmentation.ts:152-160`

#### Problem

HF Spaces on free tier (cpu-basic) sleep after ~48h inactivity. When a user hits the frontend while backend is asleep:
1. POST `/api/segment` fails with 503 or network error
2. Frontend shows generic "Failed to start job" error
3. User thinks the app is broken

Current code (lines 152-160):
```typescript
} catch (err) {
  if (err instanceof Error && err.name === 'AbortError') return
  const message = err instanceof Error ? err.message : 'Failed to start job'
  setError(message)  // <-- No 503 detection, no retry logic
  setIsLoading(false)
  setJobStatus('failed')
}
```

#### Evidence

- HF Spaces sleep behavior: [HF Docs - spaces-gpus](https://huggingface.co/docs/hub/spaces-gpus)
- Cold start time: 30-120 seconds typical

#### Required Fix

Add "waking up" state with exponential backoff retry:
```typescript
} catch (err) {
  if (err instanceof Error && err.name === 'AbortError') return

  // Detect cold start (503 or network failure)
  const is503 = err instanceof ApiError && err.status === 503
  const isNetworkError = err instanceof TypeError && err.message.includes('fetch')

  if ((is503 || isNetworkError) && retryCount < MAX_COLD_START_RETRIES) {
    setProgressMessage('Backend is waking up... Please wait.')
    setJobStatus('waking_up')
    await sleep(RETRY_DELAY * Math.pow(2, retryCount))
    return runSegmentation(caseId, fastMode, retryCount + 1)
  }

  setError(message)
  setIsLoading(false)
  setJobStatus('failed')
}
```

---

### BUG-002: CORS Regex Security Vulnerability

**Severity**: P1 - HIGH (Security)
**Impact**: Malicious HF Spaces can make cross-origin requests
**File**: `src/stroke_deepisles_demo/api/main.py:86`

#### Problem

Current regex is too permissive:
```python
allow_origin_regex=r"https://.*stroke-viewer-frontend.*\.hf\.space"
```

#### Security Test Results

```
Pattern: https://.*stroke-viewer-frontend.*\.hf\.space

MATCH: https://vibecodermcswaggins-stroke-viewer-frontend.hf.space  ✓ (legitimate)
MATCH: https://evil-stroke-viewer-frontend.hf.space                 ✗ (MALICIOUS)
MATCH: https://attacker.com-stroke-viewer-frontend-fake.hf.space    ✗ (MALICIOUS)
MATCH: https://phishing-stroke-viewer-frontend-clone.hf.space       ✗ (MALICIOUS)
```

An attacker could create a malicious HF Space with `stroke-viewer-frontend` anywhere in the name and make cross-origin requests to your backend.

#### Required Fix

Anchor the regex to your specific username:
```python
# Option A: Strict regex anchored to username
allow_origin_regex=r"https://vibecodermcswaggins-stroke-viewer-frontend\.hf\.space"

# Option B: Allow username variations but anchor pattern
allow_origin_regex=r"https://[a-z0-9]+-stroke-viewer-frontend\.hf\.space"
```

Or use explicit origin via environment variable:
```python
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "")
# Set FRONTEND_ORIGIN=https://vibecodermcswaggins-stroke-viewer-frontend.hf.space
```

---

### BUG-003: Missing COOP/COEP Headers for WebGL Performance

**Severity**: P1 - HIGH (Performance)
**Impact**: NiiVue cannot use SharedArrayBuffer, degraded performance with large medical volumes
**File**: `frontend/README.md` (HF Space config)

#### Problem

NiiVue uses WebGL2 and benefits from `SharedArrayBuffer` for optimal performance when loading large NIfTI volumes. Modern browsers require Cross-Origin Isolation headers for `SharedArrayBuffer`.

Current `frontend/README.md` has no `custom_headers`:
```yaml
---
title: Stroke Lesion Viewer
sdk: static
app_file: dist/index.html
# Missing: custom_headers for COOP/COEP
---
```

#### Evidence

- [MDN SharedArrayBuffer Security Requirements](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer#security_requirements)
- [HF Spaces custom_headers](https://huggingface.co/docs/hub/spaces-config-reference) - CONFIRMED supports COOP/COEP/CORP

#### Required Fix

Add to `frontend/README.md`:
```yaml
---
title: Stroke Lesion Viewer
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: static
app_file: dist/index.html
app_build_command: npm run build
nodejs_version: "20"
pinned: false
custom_headers:
  cross-origin-embedder-policy: require-corp
  cross-origin-opener-policy: same-origin
  cross-origin-resource-policy: cross-origin
---
```

**Note**: After adding COEP `require-corp`, ALL cross-origin resources (including the backend API) must either:
- Come from same origin, OR
- Have `Cross-Origin-Resource-Policy: cross-origin` header, OR
- Be loaded with `crossorigin` attribute

The backend already sets CORS headers, but verify NIfTI file responses include proper CORP headers.

---

## P2 - MEDIUM PRIORITY (Operational Risks)

### BUG-004: Hardware Requirements Not Enforced

**Severity**: P2 - MEDIUM
**Impact**: App fails silently if deployed on wrong hardware
**File**: `README.md`

#### Problem

Backend `README.md` specifies `suggested_hardware: t4-small` but:
1. This is only a "suggestion" - doesn't enforce GPU
2. If deployed on `cpu-basic` (free tier), DeepISLES will fail or be extremely slow
3. No runtime check or user-friendly error

#### Evidence

- `cpu-basic`: 2 vCPU, 16 GB RAM, NO GPU
- `t4-small`: T4 GPU required for DeepISLES inference
- [HF Hardware Tiers](https://huggingface.co/docs/hub/spaces-gpus)

#### Required Fix

Add runtime GPU check in backend startup:
```python
# In lifespan or startup
import torch
if not torch.cuda.is_available():
    logger.warning("GPU not available! DeepISLES requires GPU for inference.")
    # Optionally: return error response from /health endpoint
```

Document clearly in README:
```markdown
## Requirements
- **GPU Required**: This Space requires `t4-small` or better hardware.
- Free tier (`cpu-basic`) will NOT work for inference.
```

---

### BUG-005: Ephemeral Disk - Results Lost on Restart

**Severity**: P2 - MEDIUM
**Impact**: Completed job results disappear after Space restart
**File**: `src/stroke_deepisles_demo/api/routes.py:38`

#### Problem

Results are stored in `/tmp/stroke-results`:
```python
RESULTS_BASE = Path("/tmp/stroke-results")
```

HF Spaces have ephemeral filesystems by default:
- Space restart = all `/tmp` data lost
- Users with valid job IDs get 404 errors after restart
- No warning to users that results are temporary

#### Evidence

- [HF Spaces Storage](https://huggingface.co/docs/hub/spaces-storage)

#### Mitigation Options

1. **Document the limitation** (minimum fix):
   ```markdown
   ## Note
   Job results are stored temporarily and will be lost if the Space restarts.
   Download your results promptly.
   ```

2. **Enable persistent storage** (if budget allows):
   - Add `suggested_storage: small` to README.md
   - Move results to persistent volume

3. **Add result expiry warning to API**:
   ```python
   # In job response
   "warning": "Results expire after 1 hour or on Space restart"
   ```

---

### BUG-006: allow_credentials=True Unnecessary

**Severity**: P2 - MEDIUM (Security hygiene)
**Impact**: Increases CSRF surface if auth is added later
**File**: `src/stroke_deepisles_demo/api/main.py:87`

#### Problem

```python
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,  # <-- Unnecessary
    allow_methods=["*"],     # <-- Overly permissive
    allow_headers=["*"],     # <-- Overly permissive
)
```

Frontend doesn't use credentials:
```typescript
// client.ts - no credentials: 'include'
await fetch(`${this.baseUrl}/api/cases`, { signal })
```

#### Required Fix

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"...",  # Fixed as per BUG-002
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

---

## P3 - LOW PRIORITY (Documentation/Polish)

### BUG-007: WebGL2 Client Requirement Not Documented

**Severity**: P3 - LOW
**Impact**: Users with old browsers see cryptic errors
**File**: `frontend/README.md`

#### Problem

NiiVue requires WebGL2. Users on:
- Old browsers (Safari < 15, IE)
- Locked-down enterprise browsers
- Some mobile devices

Will see rendering failures with no explanation.

#### Required Fix

Add to frontend README:
```markdown
## Browser Requirements

- **WebGL2 Required**: This viewer uses NiiVue which requires WebGL2 support.
- Supported: Chrome 56+, Firefox 51+, Safari 15+, Edge 79+
- Check your browser: https://get.webgl.org/webgl2/
```

---

### BUG-008: Hardcoded Username in Production Config

**Severity**: P3 - LOW
**Impact**: Forks require manual config update
**File**: `frontend/.env.production`

#### Problem

```
VITE_API_URL=https://vibecodermcswaggins-stroke-deepisles-demo.hf.space
```

Anyone forking must update this manually.

#### Required Fix

Document in README:
```markdown
## Fork Deployment

1. Update `frontend/.env.production`:
   ```
   VITE_API_URL=https://{YOUR_USERNAME}-stroke-deepisles-demo.hf.space
   ```
2. Update CORS in `main.py` to match your frontend URL
3. Rebuild: `npm run build`
```

---

### BUG-009: FRONTEND_ORIGIN Env Var Not Explicitly Set

**Severity**: P3 - LOW
**Impact**: Relies on regex fallback, less explicit
**File**: `Dockerfile`

#### Problem

Code supports `FRONTEND_ORIGIN` but Dockerfile doesn't set it:
```python
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "")
```

#### Optional Fix

Add to Dockerfile:
```dockerfile
ENV FRONTEND_ORIGIN=https://vibecodermcswaggins-stroke-viewer-frontend.hf.space
```

---

## Configuration Verification (All PASS)

| Component | Configuration | Status |
|-----------|--------------|--------|
| CORS regex matches frontend URL | `.*stroke-viewer-frontend.*` | **PASS** |
| Backend URL in frontend build | `vibecodermcswaggins-stroke-deepisles-demo.hf.space` | **PASS** |
| `--proxy-headers` in Dockerfile | Present | **PASS** |
| Port 7860 | Configured | **PASS** |
| Results in `/tmp/` | `/tmp/stroke-results` | **PASS** |
| Async job queue | Implemented | **PASS** |

---

## Runtime Testing Checklist

| Test | Expected | Status |
|------|----------|--------|
| Frontend loads | Page renders | [ ] |
| Backend health | `{"status": "healthy"}` | [ ] |
| CORS on /api/cases | No CORS error | [ ] |
| Cold start handling | Shows "waking up" message | [ ] |
| Segmentation job | 202 + polling works | [ ] |
| NIfTI file CORS | Files load in NiiVue | [ ] |
| WebGL rendering | 3D view displays | [ ] |

---

## Priority Summary

| Priority | Count | Issues |
|----------|-------|--------|
| **P1** | 3 | Cold start handling, CORS regex security, COOP/COEP headers |
| **P2** | 3 | Hardware requirements, ephemeral disk, allow_credentials |
| **P3** | 3 | WebGL2 docs, hardcoded username, FRONTEND_ORIGIN |

---

## Sources

- [HuggingFace Spaces Config Reference](https://huggingface.co/docs/hub/spaces-config-reference)
- [HF Spaces Hardware Tiers](https://huggingface.co/docs/hub/spaces-gpus)
- [HF Spaces Storage](https://huggingface.co/docs/hub/spaces-storage)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN SharedArrayBuffer Security](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer#security_requirements)
- [MDN CORS Credentials](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Allow-Origin)
- [Uvicorn Proxy Settings](https://www.uvicorn.org/settings/)
- [NiiVue GitHub](https://github.com/niivue/niivue)
