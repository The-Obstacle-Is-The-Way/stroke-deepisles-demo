# Audit Findings - 2025-12-13 (Final)

**Date:** 2025-12-13
**Branch:** `dev`
**Status:** ALL FIXED ✓

---

## Summary

Two rounds of external agent audit findings validated and fixed:

### Round 1 Findings (P1-P4) - All Fixed in Previous Commit

| Issue | Severity | Status |
|-------|----------|--------|
| max_concurrent_jobs=10 unsafe | P1 | ✓ Fixed |
| Timeout not passed to direct invocation | P1 | ✓ Fixed |
| Slop settings removed (hf_cache_dir, temp_dir, deepisles_repo_path) | P2 | ✓ Fixed |
| P2: Prediction path mismatch (Docker mode) | P2 | ✓ Fixed |
| P3: .env.example stale TEMP_DIR reference | P3 | ✓ Fixed |
| Concurrency pre-check, logging, package description | P2-P4 | ✓ Fixed |

### Round 2 Findings (P3-P4) - Fixed in This Commit

| Issue | Severity | Status |
|-------|----------|--------|
| mypy type: ignore becomes env-dependent | P3 | ✓ Fixed |
| deployment.md describes outdated Gradio+DinD | P3 | ✓ Fixed |
| quickstart.md missing React+FastAPI path | P3 | ✓ Fixed |
| direct.py logs paths at INFO | P4 | ✓ Fixed |
| frontend fixture URLs don't match contract | P4 | ✓ Fixed |
| CLI --dataset arg "(not used yet)" | P4 | ✓ Fixed |
| pytest-asyncio config | P4 | N/A (pkg not installed) |

---

## Round 2 Fixes Detail

### P3: mypy type: ignore[import-not-found] environment-dependent

**Problem:** On machines with torch installed, mypy complains about unused ignore.

**File:** `src/stroke_deepisles_demo/api/main.py:54`

**Fix:** Added `unused-ignore` to suppress both warnings:
```python
import torch  # type: ignore[import-not-found,unused-ignore]
```

### P3: deployment.md described outdated architecture

**Problem:** Docs described Docker-in-Docker + Gradio as primary deployment.

**File:** `docs/guides/deployment.md`

**Fix:** Complete rewrite reflecting:
- React SPA frontend (Static SDK Space)
- FastAPI backend (Docker SDK Space with GPU)
- Direct invocation mode (subprocess to conda env)
- Gradio marked as legacy

### P3: quickstart.md missing React+FastAPI path

**Problem:** Only showed Gradio UI as primary option.

**File:** `docs/guides/quickstart.md`

**Fix:** Reordered options:
1. React SPA + FastAPI (Recommended)
2. CLI
3. Python API
4. Legacy Gradio UI

### P4: direct.py logged paths at INFO

**Problem:** Full input paths logged at INFO level, potentially exposing sensitive path info.

**File:** `src/stroke_deepisles_demo/inference/direct.py:158-164, 189`

**Fix:** Changed both logging calls from `logger.info` to `logger.debug`.

### P4: frontend fixture URLs don't match API contract

**Problem:** Fixture URLs were `/files/dwi.nii.gz` but actual API returns `/files/{jobId}/{caseId}/dwi.nii.gz`.

**File:** `frontend/src/test/fixtures.ts:14-15`

**Fix:** Updated URLs to match contract:
```typescript
dwiUrl: "http://localhost:7860/files/test-job-123/sub-stroke0001/dwi.nii.gz",
predictionUrl: "http://localhost:7860/files/test-job-123/sub-stroke0001/prediction.nii.gz",
```

### P4: CLI --dataset arg not wired

**Problem:** Help text said "(not used yet)".

**Files:**
- `src/stroke_deepisles_demo/cli.py:23`
- `src/stroke_deepisles_demo/data/__init__.py:34`

**Fix:**
1. Added `source` parameter to `list_case_ids()` function
2. Updated CLI to pass `args.dataset` to `list_case_ids(source=args.dataset)`
3. Updated help text to "HF dataset ID or local path"

### P4: pytest-asyncio config warning

**Claim:** pytest-asyncio emits deprecation warning about unset `asyncio_default_fixture_loop_scope`.

**Investigation:**
- pytest-asyncio is NOT installed
- No async tests in test suite
- Warning was likely from different environment

**Fix:** N/A - removed non-applicable config that was causing "unknown config option" warnings.

---

## Test Verification

```
Backend: 157 passed (pytest)
Frontend: 70 passed (vitest)
Linting: All checks passed (ruff)
Types: No issues (mypy)
```

---

## Files Modified (Round 2)

| File | Change |
|------|--------|
| `src/stroke_deepisles_demo/api/main.py` | mypy ignore fix |
| `src/stroke_deepisles_demo/inference/direct.py` | INFO → DEBUG logging |
| `src/stroke_deepisles_demo/data/__init__.py` | Added source param to list_case_ids |
| `src/stroke_deepisles_demo/cli.py` | Wired --dataset arg |
| `docs/guides/deployment.md` | Complete rewrite for React+FastAPI |
| `docs/guides/quickstart.md` | Reordered options, React first |
| `frontend/src/test/fixtures.ts` | Fixed URL contract |
| `pyproject.toml` | Removed non-applicable pytest-asyncio config |
