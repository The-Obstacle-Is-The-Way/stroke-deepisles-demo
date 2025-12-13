# Post-Refactor Audit Validation - 2024-12-13

**Context:** Senior audit performed after data loading refactor (PR #42).
**Method:** Each claim validated from first principles by reading source code.

---

## P0 Claims - VALIDATION

### CLAIM: Concurrency limiting isn't atomic (TOCTOU race)
**File:** `src/stroke_deepisles_demo/api/routes.py:92-98`

**Validation:** The concurrency check exists (BUG-006 fix):
```python
if store.get_active_job_count() >= get_settings().max_concurrent_jobs:
    raise HTTPException(status_code=503, ...)
```

**Verdict:** PARTIALLY TRUE - Fix exists but has a small TOCTOU race window between check and `create_job()`. For a demo app, this is acceptable. The worst case is N+1 jobs run instead of N.

**Status:** DOCUMENTED - Acceptable for demo, not a P0 blocker.

---

### CLAIM: No authn/authz and no rate limiting
**File:** `src/stroke_deepisles_demo/api/main.py`

**Validation:** Already documented in `docs/bugs/BUGS-AUDIT-2024-12-12.md`:
> "BUG-007 (No Authentication) was removed from audit - intentional design for public demo."

**Verdict:** FALSE - This is intentional. The app is a public demo on HuggingFace Spaces.

**Status:** NOT A BUG - Intentional design decision.

---

## P1 Claims - VALIDATION

### CLAIM: Path traversal via HF subject_id
**File:** `src/stroke_deepisles_demo/data/loader.py:104-114`

**Validation:** TRUE - `subject_id` from HF dataset is used directly in path construction:
```python
case_dir = self._temp_dir / subject_id  # No validation
```

**Mitigation:** The `subject_id` comes from the HuggingFace dataset we control, not user input. All ISLES24 subject IDs are `sub-strokeXXXX` format.

**Verdict:** TRUE (theoretical) but MITIGATED in practice. Adding validation is defense-in-depth.

**Status:** FIX - Add regex validation for defense-in-depth.

---

### CLAIM: Gradio state arbitrary delete
**File:** `src/stroke_deepisles_demo/ui/app.py:55-66`

**Validation:** TRUE - `previous_results_dir` from Gradio state used in `shutil.rmtree()`:
```python
def _cleanup_previous_results(previous_results_dir: str | None) -> None:
    prev_path = Path(previous_results_dir)
    if prev_path.exists():
        shutil.rmtree(prev_path)  # No validation!
```

Gradio state is client-side (base64 encoded JSON), potentially manipulable.

**Verdict:** TRUE - Should validate path is under allowed root.

**Status:** FIX - Add path validation.

---

### CLAIM: show_error=True exposes tracebacks
**File:** `src/stroke_deepisles_demo/ui/app.py:288`

**Validation:** TRUE
```python
get_demo().launch(
    show_error=True,  # Show full Python tracebacks in UI for debugging
)
```

**Verdict:** TRUE - Information disclosure risk. Should be configurable.

**Status:** FIX - Make configurable via settings, default to False in production.

---

### CLAIM: Unpinned GitHub Actions (supply-chain risk)
**File:** `.github/workflows/ci.yml:97,134`

**Validation:** TRUE
```yaml
uses: jlumbroso/free-disk-space@main  # Unpinned!
```

**Verdict:** TRUE - Supply-chain risk. Should pin to commit SHA.

**Status:** FIX - Pin to commit SHA.

---

### CLAIM: DeepISLES output paths mismatch
**Files:** Multiple

**Validation:** Need to verify actual output structure.

**Status:** DEFERRED - Requires integration testing to validate.

---

## P2 Claims - VALIDATION

### CLAIM: Dead Settings (hf_dataset_id, etc.)
**Files:** `src/stroke_deepisles_demo/core/config.py`

**Validation:** TRUE - `grep` shows these settings are defined but never accessed:
- `hf_dataset_id` - loader.py hardcodes `DEFAULT_HF_DATASET`
- `hf_token` - not used in new loader
- `deepisles_docker_image` - inference uses hardcoded default
- `deepisles_timeout_seconds` - not threaded through

**Verdict:** TRUE - Tech debt but not a bug. Settings exist for future use.

**Status:** DOCUMENTED - Low priority cleanup.

---

### CLAIM: Case ID reload per request
**File:** `src/stroke_deepisles_demo/api/routes.py:101`

**Validation:** TRUE - Each request calls `list_case_ids()` which may reload dataset.

**Verdict:** TRUE but ACCEPTABLE - For a demo with 149 cases, this is fine.

**Status:** DOCUMENTED - Acceptable for demo scale.

---

## P3 Claims - VALIDATION

### CLAIM: Dockerfile uv unpinned
**File:** `Dockerfile:35`

**Validation:** TRUE
```dockerfile
RUN pip install --no-cache-dir uv
```

**Verdict:** TRUE but LOW RISK - `uv.lock` pins actual dependencies. Only `uv` tool version floats.

**Status:** DOCUMENTED - Low priority.

---

### CLAIM: Docs out of date
**Files:** `DATA-PIPELINE.md`, `docs/specs/00-data-loading-refactor.md`

**Validation:** TRUE - Docs reference removed HF parquet workaround architecture.

**Status:** FIX - Update docs.

---

## P4 Claims - VALIDATION

### CLAIM: DataLoadError unused
**File:** `src/stroke_deepisles_demo/core/exceptions.py`

**Validation:** TRUE - Defined but no longer imported in data layer after refactor.

**Status:** CLEANUP - Remove or use consistently.

---

## Summary

| Finding | Severity | Status | Action |
|---------|----------|--------|--------|
| TOCTOU race in concurrency | P2 | Documented | Accept for demo |
| No auth | N/A | Documented | Intentional |
| Path traversal (subject_id) | P1 | New | Fix (defense-in-depth) |
| Gradio state arbitrary delete | P1 | New | Fix |
| show_error=True tracebacks | P1 | New | Fix |
| Unpinned GitHub Actions | P1 | New | Fix |
| Dead Settings | P3 | Documented | Accept |
| Case ID reload | P3 | Documented | Accept |
| Docs out of date | P3 | New | Fix |
| DataLoadError unused | P4 | New | Cleanup |

---

**Audited by:** Claude Code
**Date:** 2024-12-13
**Branch:** fix/post-refactor-audit
