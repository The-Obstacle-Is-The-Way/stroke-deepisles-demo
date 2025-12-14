# Remaining Issues - Post-Audit 2024-12-13

**Context:** Deep audit performed after PR #44 merged (security + config wiring fixes).
**Method:** Cross-referenced new audit against existing fixes. Validated each claim from first principles.

---

## Executive Summary

The previous PR #44 addressed many issues. This document captures **genuinely new findings** that were not previously addressed. Issues are prioritized P1-P4.

**Scope:** Fix these in branch `fix/remaining-audit-issues`

---

## P1 - High Priority (Should Fix)

### P1-001: Default max_concurrent_jobs=10 is unsafe for single GPU

**Location:** `src/stroke_deepisles_demo/core/config.py:98`

**Issue:** Default of 10 concurrent jobs can trivially trigger GPU OOM on a single GPU (HF Spaces T4 has 16GB VRAM). Even 2-3 concurrent DeepISLES runs can cause thrashing.

**Current:**
```python
max_concurrent_jobs: int = 10
```

**Fix:** Change default to 1 (safest for demo). Document tuning guidance.

**Severity:** High - can crash the demo under moderate load.

---

### P1-002: Timeout not propagated to direct invocation path

**Location:** `src/stroke_deepisles_demo/inference/deepisles.py:310-315`

**Issue:** `_run_via_direct_invocation()` doesn't pass timeout to `run_deepisles_direct()`, making `STROKE_DEMO_DEEPISLES_TIMEOUT_SECONDS` ineffective on HF Spaces.

**Current:**
```python
def _run_via_direct_invocation(..., fast: bool) -> DeepISLESResult:
    # No timeout parameter!
    result = run_deepisles_direct(
        dwi_path=dwi_path,
        adc_path=adc_path,
        output_dir=output_dir,
        flair_path=flair_path,
        fast=fast,
        # timeout missing!
    )
```

**Fix:** Add `timeout` parameter to `_run_via_direct_invocation()` and pass it through.

---

## P2 - Medium Priority (Tech Debt)

### P2-001: hf_cache_dir setting exists but is not used

**Location:** `src/stroke_deepisles_demo/core/config.py:80` + `src/stroke_deepisles_demo/data/loader.py:224`

**Issue:** `Settings.hf_cache_dir` is defined but `datasets.load_dataset()` doesn't receive `cache_dir=`. Operators setting `STROKE_DEMO_HF_CACHE_DIR` get no effect.

**Fix:** Pass `cache_dir=settings.hf_cache_dir` when set, or remove the setting.

**Decision:** Wire it in (per previous directive: wire in settings properly).

---

### P2-002: temp_dir setting exists but is not used

**Location:** `src/stroke_deepisles_demo/core/config.py:92` + `src/stroke_deepisles_demo/pipeline.py:118`

**Issue:** `Settings.temp_dir` defined but pipeline uses `tempfile.mkdtemp()` without `dir=` parameter.

**Fix:** Use `dir=settings.temp_dir` when set.

---

### P2-003: deepisles_repo_path setting exists but is not used

**Location:** `src/stroke_deepisles_demo/core/config.py:89` + `src/stroke_deepisles_demo/inference/direct.py:32-35`

**Issue:** `Settings.deepisles_repo_path` defined but direct.py hardcodes `/app` and `/opt/conda`.

**Fix:** Use setting to derive adapter path and cwd. Also wire `DEEPISLES_PATH` env var (Dockerfile:64).

---

### P2-004: Concurrency limit checked after expensive validation

**Location:** `src/stroke_deepisles_demo/api/routes.py:95-110`

**Issue:** `list_case_ids()` is called (potentially expensive HF dataset load) before checking concurrency limit. Wasted work when limit already reached.

**Fix:** Reorder to check concurrency limit first, then validate case_id.

---

### P2-005: Direct invocation logs full stdout/stderr at INFO/WARN

**Location:** `src/stroke_deepisles_demo/inference/direct.py:200-205`

**Issue:** Can explode log volume with DeepISLES's verbose output, make JSON logging invalid.

**Fix:** Log at DEBUG level, or truncate/summarize at INFO.

---

### P2-006: FastAPI doesn't apply log settings

**Location:** `src/stroke_deepisles_demo/api/main.py`

**Issue:** `STROKE_DEMO_LOG_LEVEL` and `STROKE_DEMO_LOG_FORMAT` are only applied in Gradio entrypoints. FastAPI startup doesn't call `setup_logging()`.

**Fix:** Call `setup_logging(settings.log_level, format_style=settings.log_format)` in FastAPI startup.

---

## P3 - Low Priority (Documentation/Cleanup)

### P3-001: DEEPISLES_PATH env var set but unused

**Location:** `Dockerfile:64`

**Issue:** `ENV DEEPISLES_PATH=/app` is set but direct.py doesn't read it.

**Fix:** Either wire it in (ties to P2-003) or remove from Dockerfile.

---

### P3-002: Package description still mentions Gradio

**Location:** `src/stroke_deepisles_demo/__init__.py:1`

**Issue:** Says "Gradio visualization" but primary UI is now React SPA.

**Fix:** Update description.

---

### P3-003: gradio_niivueviewer in extras but commented out in code

**Location:** `pyproject.toml:46-50` + `src/stroke_deepisles_demo/ui/components.py:7-9`

**Issue:** Extra maintenance surface for unused component.

**Fix:** Remove from extras if truly deprecated, or document scope.

---

### P3-004: Docs reference non-existent spec files

**Location:** Multiple (`deepisles.py:9`, `direct.py:15`, `viewer.py:8-9`)

**Issue:** References to `docs/specs/07-hf-spaces-deployment.md` and `docs/specs/19-perf-base64-to-file-urls.md` which don't exist (may have been archived).

**Fix:** Update doc references or point to archive location.

---

## P4 - Nitpicks (Optional Cleanup)

### P4-001: app.py doesn't pass gradio_show_error

**Location:** `app.py:32-38`

**Issue:** Root app.py doesn't pass `show_error=settings.gradio_show_error` like ui/app.py does.

**Fix:** Pass consistently.

---

### P4-002: "json" log format is not valid JSON

**Location:** `src/stroke_deepisles_demo/core/logging.py:30`

**Issue:** JSON format doesn't escape message content, breaks if messages contain quotes/newlines.

**Fix:** Use proper JSON formatter (e.g., `python-json-logger`).

---

### P4-003: create_staging_directory is unused

**Location:** `src/stroke_deepisles_demo/data/staging.py:93`

**Issue:** Dead code surface.

**Fix:** Remove or integrate via temp_dir setting.

---

### P4-004: DatasetInfo class is unused

**Location:** `src/stroke_deepisles_demo/data/loader.py:45`

**Issue:** Defined but never instantiated.

**Fix:** Remove or wire into API responses.

---

### P4-005: HEAD method comment is incorrect

**Location:** `src/stroke_deepisles_demo/api/main.py:108-109`

**Issue:** Comment says "HEAD for preflight checks" but CORS preflight uses OPTIONS.

**Fix:** Fix comment.

---

## Already Fixed (PR #44) - Confirmed

These issues from the audit were **already addressed**:

| Issue | Status | Evidence |
|-------|--------|----------|
| Docker build missing `--extra api` | FIXED | Dockerfile:44 |
| hf_dataset_id not wired | FIXED | loader.py:217 |
| hf_token not wired | FIXED | loader.py:218-224 |
| deepisles_docker_image not wired | FIXED | deepisles.py:153-155 |
| deepisles_timeout_seconds not wired | FIXED | pipeline.py:93-95 |
| deepisles_use_gpu not wired | FIXED | pipeline.py:91-93 |
| TOCTOU race in concurrency | FIXED | routes.py:107-110 (atomic create_job_if_under_limit) |
| File extension allowlist | FIXED | files.py:28 |
| Path traversal in subject_id | FIXED | loader.py:111-115 |
| Stale StaticFiles comment | FIXED | Dockerfile:70 |

---

## Intentional / Non-Issues

| Claim | Verdict | Reason |
|-------|---------|--------|
| No auth/rate limiting | NON-ISSUE | Intentional for public demo |
| Dataset reload per request | ACCEPTABLE | Demo scale (149 cases), adds negligible latency |
| Docker-mode file URL mismatch | NON-ISSUE | `find_prediction_mask()` returns actual path, pipeline copies to `results_dir/{case_id}/` correctly |

---

## Fix Order

1. **P1-001**: max_concurrent_jobs default (safety)
2. **P1-002**: Timeout propagation to direct invocation
3. **P2-004**: Reorder concurrency check before validation
4. **P2-001, P2-002, P2-003**: Wire in remaining dead settings
5. **P2-005, P2-006**: Logging fixes
6. **P3-***: Documentation cleanup
7. **P4-***: Nitpicks (time permitting)

---

**Auditor:** Claude Code
**Date:** 2024-12-13
**Target Branch:** `fix/remaining-audit-issues`
