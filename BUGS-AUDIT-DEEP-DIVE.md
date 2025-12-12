# Deep Dive Audit: Additional Bugs and Anti-Patterns

**Date**: 2025-12-12
**Auditor**: Claude Code Deep Dive
**Scope**: Full codebase audit beyond initial HF Spaces integration issues

---

## Executive Summary

Following the HF Spaces integration fixes (BUGS-HF-SPACES-INTEGRATION.md), this audit examined the entire codebase for hidden bugs, anti-patterns, silent failures, and incomplete implementations. Several issues were found that could impact reliability and debuggability.

---

## P1 - HIGH PRIORITY

### BUG-010: Missing Error Boundary in React App

**Severity**: P1 - HIGH
**Impact**: Unhandled React errors crash entire frontend
**File**: `frontend/src/App.tsx`

#### Problem

No React Error Boundary wraps the application. If NiiVueViewer (WebGL), ProgressIndicator, or any component throws during render:
1. Entire app crashes to white screen
2. User loses all progress/state
3. No user-friendly error message

#### Evidence

```tsx
// App.tsx - No error boundary
export default function App() {
  return (
    <Layout>
      {/* If any child throws, app crashes */}
      <NiiVueViewer ... />  // WebGL can throw
    </Layout>
  )
}
```

#### Fix Required

Add ErrorBoundary component wrapping the main app content.

**Status**: Fixed in this commit

---

### BUG-011: Bare Exception Suppression Loses Diagnostic Info

**Severity**: P1 - HIGH
**Impact**: Silent failures impossible to debug
**File**: `src/stroke_deepisles_demo/api/routes.py:230-231`

#### Problem

```python
with contextlib.suppress(Exception):
    volume_ml = round(compute_volume_ml(result.prediction_mask, threshold=0.5), 2)
```

This suppresses ALL exceptions including:
- FileNotFoundError (mask file missing)
- ValueError (invalid threshold)
- MemoryError (volume too large)
- AttributeError (bad prediction object)

When `volume_ml` is `None`, users have no idea why.

#### Fix Required

Log the exception, return None only for expected errors.

**Status**: Fixed in this commit

---

### BUG-012: No Case ID Validation Before Job Creation

**Severity**: P1 - MEDIUM
**Impact**: Jobs fail after 30+ seconds instead of immediately
**File**: `src/stroke_deepisles_demo/api/routes.py:81-103`

#### Problem

```python
def create_segment_job(..., body: SegmentRequest, ...):
    # body.case_id is trusted without validation
    store.create_job(job_id, body.case_id, body.fast_mode)
    # If case_id is invalid, job fails later with confusing error
```

If a user submits an invalid case ID like "nonexistent-case", the job is created, but fails ~30 seconds later with a generic "Segmentation failed" message.

#### Fix Required

Validate case_id exists before creating job, return 400 immediately if invalid.

**Status**: Fixed in this commit

---

## P2 - MEDIUM PRIORITY

### BUG-013: Silent JSON Parse Failures in API Client

**Severity**: P2 - MEDIUM
**Impact**: Generic error messages instead of server details
**File**: `frontend/src/api/client.ts:50,85,120`

#### Problem

```typescript
const error = await response.json().catch(() => ({}))
// If JSON parsing fails, error becomes {} and error.detail is undefined
```

When the backend returns malformed JSON or HTML (502 proxy error pages), the error message becomes generic because `error.detail` is undefined.

#### Fix Required

Log parse failures in development, provide more context in error messages.

**Status**: Fixed in this commit

---

### BUG-014: Job Store Thread Safety Concern

**Severity**: P2 - LOW (in practice)
**Impact**: Potential race conditions in multi-worker deployment
**File**: `src/stroke_deepisles_demo/api/job_store.py:183-193`

#### Problem

```python
def get_job(self, job_id: str) -> Job | None:
    with self._lock:
        return self._jobs.get(job_id)  # Returns reference, not copy

# Caller can then modify returned job outside lock
job = store.get_job(job_id)
if job:
    job.status = JobStatus.RUNNING  # Race if another thread modifies
```

#### Mitigating Factors

- HF Spaces runs single uvicorn worker
- Code comments explicitly document this limitation
- All mutation methods use locks

#### Recommendation

Document that multi-worker deployment requires shared store (Redis).

**Status**: Documented, low-priority fix

---

### BUG-015: HuggingFace Dataset Temp Directory Leak on Exception

**Severity**: P2 - MEDIUM
**Impact**: Orphaned temp directories if download fails
**File**: `src/stroke_deepisles_demo/data/adapter.py:216-223`

#### Problem

```python
if self._temp_dir is None:
    self._temp_dir = Path(tempfile.mkdtemp(prefix="isles24_hf_"))

# If _download_case_from_parquet() raises AFTER temp dir creation,
# and caller doesn't use context manager, temp dir leaks
case_data = self._download_case_from_parquet(file_idx, subject_id)
```

#### Mitigating Factors

- Pipeline code uses context manager correctly
- Temp directory is small (~50MB per case)
- HF Spaces ephemeral storage clears on restart

#### Status

Low-priority, documented

---

## P3 - LOW PRIORITY

### BUG-016: Console.warn with Untyped Error

**Severity**: P3 - LOW
**Impact**: Potential uncaught exception in error logging
**File**: `frontend/src/hooks/useSegmentation.ts:115`

```typescript
console.warn('Polling error (will retry):', err)
// If err is circular object, could cause issues
```

---

### BUG-017: Hardcoded NIfTI Output Filename Detection

**Severity**: P3 - LOW
**Impact**: Fragile if DeepISLES changes output naming
**File**: `src/stroke_deepisles_demo/inference/deepisles.py:96-117`

```python
possible_names = [
    "prediction.nii.gz",
    "pred.nii.gz",
    # ... many hardcoded names
]
```

If DeepISLES updates output naming convention, code silently picks wrong file.

---

### BUG-018: Subprocess Stderr Potentially Exposed

**Severity**: P3 - LOW (Security)
**Impact**: Internal paths/config may leak to frontend
**File**: `src/stroke_deepisles_demo/inference/direct.py:207-211`

```python
raise DeepISLESError(
    f"DeepISLES inference failed with exit code {result.returncode}. "
    f"stderr: {result.stderr}"  # May contain sensitive paths
)
```

This is logged but sanitized before reaching the frontend (routes.py:264 returns generic message).

---

### BUG-019: Unused Frontend Dependencies

**Severity**: P3 - LOW
**Impact**: Bundle size bloat
**File**: `frontend/package.json`

These dependencies appear unused:
- `cropperjs` - No image cropping in the app
- `lazy-brush` - No brush/drawing functionality
- `resize-observer-polyfill` - Modern browsers don't need this

---

## Issues Already Fixed (This PR)

| Bug ID | Issue | Fix |
|--------|-------|-----|
| BUG-001 | Cold Start / 503 Handling | Added `waking_up` state with retry |
| BUG-002 | CORS Regex Security | Anchored to specific origin |
| BUG-003 | COOP/COEP Headers | Added custom_headers |
| BUG-004 | Hardware Requirements | Documented GPU needs |
| BUG-005 | Ephemeral Disk Warning | Added warning to results |
| BUG-007 | WebGL2 Documentation | Added browser requirements |
| BUG-008 | Fork Deployment Docs | Added instructions |
| BUG-009 | FRONTEND_ORIGIN | Added to Dockerfile |

---

## Code Quality Observations

### Positive Patterns Found

1. **Thread-safe job store** - Proper RLock usage for mutations
2. **Context manager for datasets** - Ensures temp file cleanup
3. **Path traversal protection** - Job ID validation, path.is_relative_to() checks
4. **Typed API contracts** - Pydantic schemas match TypeScript types
5. **Graceful WebGL cleanup** - Forces context loss to free GPU memory
6. **Exponential backoff** - Proper retry logic for cold starts

### Anti-Patterns Found

1. **Bare exception suppression** - `contextlib.suppress(Exception)` hides bugs
2. **Silent JSON parse fallback** - `.catch(() => ({}))` loses error info
3. **No input validation** - Case ID not validated before job creation
4. **Missing error boundary** - React crashes not caught

---

## Web Research Findings

Based on December 2025 HuggingFace Spaces documentation and forum discussions:

1. **504 Gateway Timeouts** ([HF Forums](https://discuss.huggingface.co/t/504-gateway-timeout-with-http-request/24018)): Gradio/FastAPI requests timing out after 60s. Our async job queue pattern correctly handles this.

2. **CORS with Private Spaces** ([HF Forums](https://discuss.huggingface.co/t/getting-a-cors-error-when-embedding-the-my-private-space/142466)): CORS errors when embedding private spaces. Our public space configuration is correct.

3. **custom_headers Support** ([HF Docs](https://huggingface.co/docs/hub/spaces-config-reference)): Confirmed that COEP/COOP/CORP headers are supported in static spaces. Our configuration matches documentation.

4. **SharedArrayBuffer Requirements** ([Chrome Blog](https://developer.chrome.com/blog/enabling-shared-array-buffer)): Cross-origin isolation required for SharedArrayBuffer. Our headers enable this correctly.

---

## Summary Table

| Priority | Count | Status |
|----------|-------|--------|
| **P1** | 3 | Fixed in this PR |
| **P2** | 3 | 1 Fixed, 2 Documented |
| **P3** | 4 | Documented |

---

## Sources

- [HuggingFace Spaces Config Reference](https://huggingface.co/docs/hub/spaces-config-reference)
- [HF Forum: 504 Gateway Timeout](https://discuss.huggingface.co/t/504-gateway-timeout-with-http-request/24018)
- [HF Forum: CORS Issues](https://discuss.huggingface.co/t/cors-issue-with-huggingface-spaces-and-netlify-hosted-react-app/62634)
- [Chrome: SharedArrayBuffer Requirements](https://developer.chrome.com/blog/enabling-shared-array-buffer)
- [GitHub: COEP/COOP Headers Issue](https://github.com/huggingface/huggingface_hub/issues/1525)
