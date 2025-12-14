# Post-Audit Findings - Validated from First Principles

**Date:** 2025-12-13
**Branch:** `fix/remaining-audit-issues`
**Context:** Re-review of external agent audit findings after initial fix implementation

---

## Summary

After deep-dive validation of the external agent's re-review findings, I've confirmed:

| Claim | Status | Severity | Action |
|-------|--------|----------|--------|
| P2: /files URL mismatch | **VALID** (Docker mode only) | P2 | Fix required |
| P3: .env.example stale reference | **VALID** | P3 | Fix required |
| P4: Path logging at INFO | **VALID** | P4 | Optional |

---

## P2: Prediction File URL Mismatch (Docker Mode Only)

### The Claim
> If DeepISLES writes to `results/` subdirectory, the frontend's predictionUrl will 404.

### Validation - CONFIRMED

**Root Cause:** Two different `find_prediction_mask()` functions with inconsistent behavior:

1. **`deepisles.py:84-132`** (Docker mode) - searches `output_dir/results/` FIRST
2. **`direct.py:69-99`** (HF Spaces mode) - searches `output_dir/` ONLY

**The Bug Flow (Docker mode only):**

```
1. Pipeline sets: results_dir = /tmp/stroke-results/{job_id}/{case_id}

2. Docker mounts results_dir as /app/output

3. If DeepISLES writes to /app/output/results/prediction.nii.gz
   → Host sees: results_dir/results/prediction.nii.gz

4. deepisles.py:find_prediction_mask() returns:
   → /tmp/stroke-results/{job_id}/{case_id}/results/prediction.nii.gz

5. routes.py:270 extracts just the filename:
   → pred_filename = result.prediction_mask.name  # "prediction.nii.gz"

6. URL built as:
   → /files/{job_id}/{case_id}/prediction.nii.gz

7. files.py:62 looks for:
   → results_dir/{job_id}/{case_id}/prediction.nii.gz

8. But actual file is at:
   → results_dir/{job_id}/{case_id}/results/prediction.nii.gz

9. Result: 404 Not Found
```

**Evidence:**
- `deepisles.py:101-103`: Explicitly searches `results/` subdir first
- `deepisles.py:294-295`: Docstring example shows `results/` path
- `routes.py:270`: Uses `.name` which strips parent directories
- `files.py:62`: Constructs flat path without `results/` component

**Why HF Spaces mode is NOT affected:**
- `direct.py:find_prediction_mask()` only searches `output_dir/` directly
- DeepISLES in direct mode outputs `lesion_msk.nii.gz` to `output_dir/` root
- Path matches URL expectation

**Fix Options:**

| Option | Pros | Cons |
|--------|------|------|
| A. Copy prediction to case root after finding | Clean URL contract, simple | Extra I/O |
| B. Include relative path in URL | Accurate path | Breaks URL contract, complex routing |
| C. Search subdirs in files.py | Flexible | Security concern (path traversal surface) |

**Recommended Fix:** Option A - copy/move prediction to expected location after `find_prediction_mask()`.

---

## P3: .env.example Stale Reference

### The Claim
> `.env.example` still references removed `STROKE_DEMO_TEMP_DIR`

### Validation - CONFIRMED

**Evidence:** `.env.example:17`
```bash
# STROKE_DEMO_TEMP_DIR=/tmp/custom_temp
```

This setting was removed from `config.py` as part of the slop cleanup (duplicates native `TMPDIR`).

**Fix:** Remove the line or replace with comment about using native `TMPDIR`.

---

## P4: Path Logging at INFO Level (Minor)

### The Claim
> Direct invocation logs full input paths at INFO, which may be noisier than intended given the "medical domain" logging posture.

### Validation - CONFIRMED but LOW PRIORITY

**Evidence:** `direct.py:158-164, 189`
```python
logger.info(
    "Running DeepISLES via subprocess: dwi=%s, adc=%s, flair=%s, fast=%s",
    dwi_path, adc_path, flair_path, fast,
)
...
logger.info("Subprocess command: %s", " ".join(cmd))
```

**Context:**
- `routes.py` explicitly avoids logging `case_id` ("may be sensitive - medical domain")
- However, `direct.py` logs full paths which could contain case identifiers
- The main "log explosion" issue (stdout/stderr) was fixed (moved to DEBUG)

**Assessment:** This is P4 (minor). The major logging issue was addressed. Path logging at startup is reasonable for debugging, though could be moved to DEBUG for stricter privacy posture.

**Recommendation:** Keep as-is for now, or optionally move to DEBUG if strict privacy is required.

---

## Action Plan

### Must Fix (Before Merge)

1. **P2: Prediction path mismatch** - Copy prediction to case root after finding
   - File: `src/stroke_deepisles_demo/inference/deepisles.py`
   - After `find_prediction_mask()`, copy file to `output_dir/` if it's in a subdirectory

2. **P3: .env.example cleanup**
   - File: `.env.example`
   - Remove line 17 (`STROKE_DEMO_TEMP_DIR`)

### Optional (P4)

3. **Path logging** - Move to DEBUG if strict privacy required
   - File: `src/stroke_deepisles_demo/inference/direct.py`
   - Lines 158-164, 189

---

## Test Verification

After fixes, verify:
```bash
# All tests pass
PYTHONPATH=src pytest -q

# Lint/type checks pass
uv run ruff check src tests
uv run mypy src
```

---

## Files to Modify

| File | Change |
|------|--------|
| `src/stroke_deepisles_demo/inference/deepisles.py` | Copy prediction to expected location |
| `.env.example` | Remove stale TEMP_DIR reference |
| (Optional) `src/stroke_deepisles_demo/inference/direct.py` | Move path logging to DEBUG |
