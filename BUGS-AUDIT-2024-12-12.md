# Bug Audit Report - 2024-12-12

Consolidated audit findings validated from first principles by reading source code.
**Status: FIXED** - P1 and P2 bugs addressed in PR #40.

---

## P1 - High Priority (Functional Bugs)

### BUG-005: Exception Handling Converts 400→500

**File:** `src/stroke_deepisles_demo/api/routes.py:127-129`

**Issue:** The exception handler catches ALL exceptions including HTTPException,
converting intentional 400 Bad Request responses into 500 Internal Server Errors.

```python
# Lines 96-99: Raises 400 for invalid case_id
if body.case_id not in valid_cases:
    raise HTTPException(
        status_code=400,
        detail=f"Invalid case ID: '{body.case_id}'. Use GET /api/cases for available cases.",
    )

# Lines 127-129: BUG - catches the HTTPException above and converts to 500
except Exception:
    logger.exception("Failed to create segmentation job")
    raise HTTPException(status_code=500, detail="Failed to create segmentation job") from None
```

**Impact:** Frontend receives 500 errors for invalid input, making debugging difficult.

**Fix:** Add `except HTTPException: raise` before `except Exception:` to re-raise HTTP exceptions.

---

### BUG-006: Unbounded Concurrent Inference

**Files:** `src/stroke_deepisles_demo/api/routes.py`, `src/stroke_deepisles_demo/api/main.py`

**Issue:** No rate limiting, semaphores, or concurrency controls exist. Every request
spawns a GPU-bound background task without limits.

**Validation:** `grep -r "semaphore|rate.?limit|concurrent|max.*jobs|throttl"` returns 0 hits.

**Impact:**
- N concurrent requests = N GPU inference tasks = OOM or GPU memory exhaustion
- Denial of service risk (intentional or accidental)
- HF Spaces free tier could be overwhelmed

**Fix Options:**
1. Add `asyncio.Semaphore(1)` to limit concurrent inference
2. Add job queue depth limit (reject if >N pending jobs)
3. Add rate limiting middleware (slowapi or similar)

---

## P2 - Medium Priority (Resource Leaks, Misconfigurations)

### BUG-008: Temp Directory Leak in Convenience Functions

**File:** `src/stroke_deepisles_demo/data/__init__.py:20-34`

**Issue:** `get_case()` and `list_case_ids()` create dataset instances without using
the context manager, causing temp directory accumulation.

```python
def get_case(case_id: str | int) -> CaseFiles:
    dataset = load_isles_dataset()  # Creates temp dir internally
    return dataset.get_case(case_id)  # cleanup() never called!

def list_case_ids() -> list[str]:
    dataset = load_isles_dataset()  # Creates temp dir internally
    return dataset.list_case_ids()  # cleanup() never called!
```

**Validation:** The loader.py docstring explicitly says:
> "Use as context manager: `with load_isles_dataset() as ds: ...` for automatic cleanup"

**Impact:** Unbounded /tmp growth over time, eventual disk exhaustion.

**Fix:** Refactor to use context manager or call `dataset.cleanup()` explicitly.

---

### BUG-009: Results Directory Configuration Drift

**Files:**
- `src/stroke_deepisles_demo/core/config.py:93` → `results_dir: Path = Path("./results")`
- `src/stroke_deepisles_demo/api/config.py:10` → `RESULTS_DIR = Path("/tmp/stroke-results")`

**Issue:** Two different default values for results directory in two config modules.
API uses `/tmp/stroke-results`, core uses `./results`.

**Impact:**
- Confusion about canonical location
- Risk of code using wrong config and writing to wrong location
- core/config.py's `./results` won't work on HF Spaces (not writable)

**Fix:** Consolidate to single source of truth. Remove one or make them reference each other.

---

### BUG-010: Case ID Logged Despite Sensitivity Comment

**File:** `src/stroke_deepisles_demo/api/routes.py:264`

**Issue:** Code explicitly logs case_id despite comment on line 118 saying not to:

```python
# Line 118 (comment):
# Note: Don't log case_id as it may be sensitive (medical domain)

# Line 264 (violation):
logger.info(
    "Job %s completed: case=%s, dice=%.3f, time=%.1fs",
    job_id,
    case_id,  # <-- Logged here
    result.dice_score or 0,
    result.elapsed_seconds,
)
```

**Impact:** Potential PHI/PII exposure in logs if case IDs contain patient identifiers.

**Fix:** Remove `case=%s` from log format string and remove `case_id` argument.

---

### BUG-011: Frontend Mock Filenames Don't Match Real Backend

**Files:**
- `frontend/src/mocks/handlers.ts:167-168`
- `src/stroke_deepisles_demo/api/routes.py:246-256`
- `src/stroke_deepisles_demo/pipeline.py:123`
- `src/stroke_deepisles_demo/inference/direct.py:85`

**Issue:** Mock uses different filenames than actual backend output:

| File Type | Mock (handlers.ts) | Real Backend |
|-----------|-------------------|--------------|
| DWI | `dwi.nii.gz` | `{case_id}_dwi.nii.gz` |
| Prediction | `prediction.nii.gz` | `lesion_msk.nii.gz` |

**Validation:**
- Mock: `dwiUrl: \`\${API_BASE}/files/\${jobId}/\${updatedJob.caseId}/dwi.nii.gz\``
- Backend pipeline.py:123: `dwi_dest = results_dir / f"{resolved_case_id}_dwi.nii.gz"`
- Backend direct.py:85: `expected_path = output_dir / "lesion_msk.nii.gz"`

**Impact:** Frontend tests pass but fail in production. Integration gap.

**Fix:** Update mock to match actual backend output filenames.

---

## P3 - Low Priority (Observability, Best Practices)

### BUG-012: Loose Dependency Pinning

**Files:**
- `pyproject.toml` - Uses `>=` ranges (e.g., `fastapi>=0.115.0`)
- `frontend/package.json` - Uses `^` ranges (e.g., `"react": "^19.2.0"`)

**Issue:** Dependencies use loose version ranges instead of exact pins.

**Impact:** Non-reproducible builds. Breaking changes in minor updates could cause silent failures.

**Note:** Lock files (uv.lock, package-lock.json) may mitigate this if checked in.

---

## Validated as FALSE (Not Bugs)

### CLAIM: .env tracked despite .gitignore
**Status:** FALSE
**Validation:** `git ls-files .env` returns empty. File is not tracked.

### CLAIM: CORS missing .static.hf.space variant
**Status:** LIKELY FALSE
**Validation:** HuggingFace Static Spaces use `.hf.space` domain, not `.static.hf.space`.
The current CORS config includes `https://vibecodermcswaggins-stroke-viewer-frontend.hf.space`.

---

## Fix Status

| Bug | Status | PR |
|-----|--------|-----|
| BUG-005 | ✅ FIXED | #40 |
| BUG-006 | ✅ FIXED | #40 |
| BUG-008 | ✅ FIXED | #40 |
| BUG-009 | 🔄 DEFERRED | See NEXT-CONCERNS.md |
| BUG-010 | ✅ FIXED | #40 |
| BUG-011 | ✅ FIXED | #40 |
| BUG-012 | 🔄 DEFERRED | See NEXT-CONCERNS.md |

## Notes

1. **BUG-004 (StaticFiles CORS bypass)** was already fixed in the codebase via `files.py` router.
   The fix comment at `api/main.py:131-132` documents this.

2. **BUG-007 (No Authentication)** was removed from audit - intentional design for public demo.

---

**Audited by:** Claude Code
**Date:** 2024-12-12
**Fixed:** 2024-12-12 (PR #40)
