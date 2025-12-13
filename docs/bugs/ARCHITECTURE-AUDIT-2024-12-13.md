# Architecture Audit - 2024-12-13

**Auditor**: Claude Code (validating external analysis)
**Date**: 2024-12-13
**Status**: VALIDATED - Fixes in branch `fix/architecture-audit`

## Summary

External audit identified multiple issues. This document validates each claim from first principles
and documents the fix strategy. Per user directive: **wire in settings properly rather than removing them**.

---

## P0 - Critical (Release Blockers)

### P0-001: Docker build missing API extras ⚠️ CONFIRMED

**Location**: `Dockerfile:43` + `Dockerfile:94`

**Claim**: Container runs uvicorn but `uv sync --no-dev --no-install-project` doesn't include `--extra api`.

**Validation**:
```dockerfile
# Line 43: Dependencies installed without API extra
RUN uv sync --frozen --no-dev --no-install-project

# Line 94: But CMD requires uvicorn (which is in api extra!)
CMD ["uvicorn", "stroke_deepisles_demo.api.main:app", ...]
```

In `pyproject.toml`:
```toml
[project.optional-dependencies]
api = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
]
```

**Impact**: Container will crash at runtime with `ModuleNotFoundError: No module named 'uvicorn'`

**Fix**:
```dockerfile
RUN uv sync --frozen --no-dev --no-install-project --extra api
```

---

## P1 - High Priority

### P1-001: Makefile install doesn't include extras ⚠️ CONFIRMED (Minor)

**Location**: `Makefile:4`

**Claim**: `make install` runs `uv sync` without extras.

**Validation**: `uv sync` in dev mode does include dev dependencies but NOT optional extras.
Tests requiring FastAPI/Gradio may fail.

**Impact**: Low for dev (most devs run tests via `uv run pytest`), but inconsistent.

**Fix**: Update Makefile to install extras needed for testing:
```makefile
install:
    uv sync --extra api --extra gradio
```

### P1-002: Stale Dockerfile comment about StaticFiles ⚠️ CONFIRMED

**Location**: `Dockerfile:69`

**Claim**: Comment says "StaticFiles mount" but we use explicit routes.

**Validation**:
```dockerfile
# Line 69: STALE COMMENT
# CRITICAL: /tmp/stroke-results is required for FastAPI StaticFiles mount

# But files.py:1-16 explicitly says we REPLACED StaticFiles:
# "BUG-004 FIX: This module replaces the StaticFiles mount approach."
```

**Impact**: Misleads operators debugging file-serving issues.

**Fix**: Update comment to reflect explicit route implementation.

---

## P2 - Medium Priority (Dead Config → Wire In)

### P2-001: hf_dataset_id setting not used ⚠️ CONFIRMED

**Location**: `config.py:79` → `loader.py:213`

**Claim**: `Settings.hf_dataset_id` exists but `load_isles_dataset()` uses hardcoded `DEFAULT_HF_DATASET`.

**Validation**:
```python
# config.py:79
hf_dataset_id: str = "hugging-science/isles24-stroke"

# loader.py:158 (hardcoded duplicate!)
DEFAULT_HF_DATASET = "hugging-science/isles24-stroke"

# loader.py:213 (ignores settings)
dataset_id = str(source) if source else DEFAULT_HF_DATASET
```

**Fix**: Wire `get_settings().hf_dataset_id` through the data loading path.

### P2-002: hf_token setting not used ⚠️ CONFIRMED

**Location**: `config.py:81` → `loader.py:218`

**Claim**: `Settings.hf_token` exists but isn't passed to `datasets.load_dataset()`.

**Validation**:
```python
# config.py:81
hf_token: str | None = Field(default=None, repr=False)

# loader.py:218 (no token!)
ds = load_dataset(dataset_id, split="train")
```

**Fix**: Pass `token=get_settings().hf_token` to `load_dataset()`.

### P2-003: deepisles_docker_image setting ignored ⚠️ CONFIRMED

**Location**: `config.py:84` → `deepisles.py:34`

**Claim**: Settings exists but hardcoded constant `DEEPISLES_IMAGE` is used.

**Validation**:
```python
# config.py:84
deepisles_docker_image: str = "isleschallenge/deepisles"

# deepisles.py:34 (hardcoded!)
DEEPISLES_IMAGE = "isleschallenge/deepisles"

# deepisles.py:169 (uses constant, not settings)
run_container(DEEPISLES_IMAGE, ...)
```

**Fix**: Use `get_settings().deepisles_docker_image` in `_run_via_docker()`.

### P2-004: deepisles_timeout_seconds setting not wired through ⚠️ CONFIRMED

**Location**: `config.py:86` → `pipeline.py` → `deepisles.py:242`

**Claim**: Timeout setting exists but pipeline doesn't pass it.

**Validation**:
```python
# config.py:86
deepisles_timeout_seconds: int = 1800

# pipeline.py:148-153 (no timeout parameter!)
inference_result = run_deepisles_on_folder(
    staged.input_dir,
    output_dir=results_dir,
    fast=fast,
    gpu=gpu,
    # timeout missing!
)
```

**Fix**: Pass `timeout=get_settings().deepisles_timeout_seconds` through pipeline.

### P2-005: deepisles_use_gpu setting not used by API ⚠️ CONFIRMED

**Location**: `config.py:87` → `routes.py:232`

**Claim**: GPU setting exists but API path doesn't pass it.

**Validation**:
```python
# config.py:87
deepisles_use_gpu: bool = True

# routes.py:232-238 (no gpu parameter!)
result = run_pipeline_on_case(
    case_id,
    output_dir=output_dir,
    fast=fast_mode,
    compute_dice=True,
    cleanup_staging=True,
    # gpu missing!
)
```

**Fix**: Pass `gpu=get_settings().deepisles_use_gpu` through API route.

### P2-006: Dataset reloaded on every /api/cases call ⚠️ CONFIRMED

**Location**: `routes.py:49` → `data/__init__.py:34`

**Claim**: `list_case_ids()` reloads dataset each time.

**Validation**:
```python
# data/__init__.py:34-41
def list_case_ids() -> list[str]:
    with load_isles_dataset() as dataset:  # Fresh load every call!
        return dataset.list_case_ids()
```

**Impact**: Unnecessary latency on cold paths, amplifies HF wake-up time.

**Fix**: Add TTL cache for case IDs list.

### P2-007: Double dataset load on segment request ⚠️ CONFIRMED

**Location**: `routes.py:101` → `pipeline.py:90`

**Claim**: Validation loads dataset, then pipeline loads again.

**Validation**:
```python
# routes.py:101
valid_cases = list_case_ids()  # First load

# Then in run_pipeline_on_case (routes.py:232)
# pipeline.py:90
with load_isles_dataset() as dataset:  # Second load!
```

**Fix**: Remove validation pre-check, let pipeline raise controlled error.

### P2-008: File download has no extension allowlist ⚠️ CONFIRMED (Low Risk)

**Location**: `files.py:29`

**Claim**: Any file under job dir is servable.

**Validation**: Path traversal is blocked, but no extension filter.
Currently only NIfTI files end up in results dirs, but defense-in-depth is better.

**Fix**: Add extension allowlist: `.nii`, `.nii.gz`.

### P2-009: Concurrency limit check-then-create not atomic ⚠️ CONFIRMED (Mitigated)

**Location**: `routes.py:92-113`

**Claim**: TOCTOU race in concurrency limiting.

**Validation**:
```python
# routes.py:92-98
if store.get_active_job_count() >= max:  # Check
    raise 503
# ... other code ...
store.create_job(job_id, ...)  # Create (gap!)
```

**Mitigation**: Single-worker uvicorn (no multi-worker race). But code smell remains.

**Fix**: Add atomic `create_job_if_under_limit()` method to JobStore.

### P2-010: Gradio cleanup scope mismatch ⚠️ CONFIRMED

**Location**: `ui/app.py:67` + `pipeline.py:107`

**Claim**: Gradio cleanup only checks `results_dir`, but pipeline creates temp in system temp.

**Validation**:
```python
# ui/app.py:67
allowed_root = get_settings().results_dir.resolve()

# pipeline.py:107 (when output_dir is None)
base_temp = Path(tempfile.mkdtemp(prefix="deepisles_pipeline_"))
# Creates in /tmp, NOT in results_dir!
```

**Impact**: Disk leak - Gradio UI's temp files never cleaned up.

**Fix**: Pass `output_dir=get_settings().results_dir / unique_id` from Gradio UI to pipeline.

---

## P3 - Low Priority (Documentation/Metadata)

### P3-001: Root app.py has stale deployment comment ⚠️ CONFIRMED

**Location**: `app.py:4`

**Claim**: Says HF Spaces uses `ui.app` but Dockerfile runs `api.main`.

**Current**:
```python
# NOTE: HuggingFace Spaces Docker deployment uses `python -m stroke_deepisles_demo.ui.app`
```

**Fix**: Update to reference `api.main:app` via uvicorn.

### P3-002: pyproject.toml description mentions Gradio ⚠️ CONFIRMED

**Location**: `pyproject.toml:4`

**Current**:
```toml
description = "Demo: HF datasets + DeepISLES stroke segmentation + Gradio visualization"
```

**Fix**: Update to mention React SPA + FastAPI as primary, Gradio as legacy.

### P3-003: README describes Gradio as visualization layer ⚠️ CONFIRMED

**Location**: `README.md:37`

**Current**:
```markdown
3. **Visualization**: Interactive 3D and multi-planar viewing with NiiVue in Gradio.
```

**Fix**: Update to describe React SPA + FastAPI architecture, note Gradio as legacy option.

### P3-004: requirements.txt exists alongside uv.lock ⚠️ CONFIRMED

**Location**: `requirements.txt` + `Dockerfile:31`

**Validation**: requirements.txt exists (547 bytes) but Dockerfile only uses uv.lock.

**Fix**: Either remove requirements.txt or add comment clarifying it's for pip-only environments.

---

## P4 - Nitpicks (Code Cleanliness)

### P4-001: pipeline.py dataset_id parameter ignored ⚠️ CONFIRMED

**Location**: `pipeline.py:60`

```python
dataset_id: str | None = None,  # Accepted
# ...
_ = dataset_id  # But explicitly ignored (line 84)
```

**Fix**: Wire `dataset_id` through to `load_isles_dataset()`.

### P4-002: pipeline.py max_workers parameter ignored ⚠️ CONFIRMED

**Location**: `pipeline.py:186`

```python
max_workers: int = 1,  # Accepted
# ...
_ = max_workers  # Explicitly ignored (line 206)
```

**Note**: Docstring correctly says "Currently ignored - reserved for future parallel support."
This is acceptable tech debt - parameter exists for API stability.

**Fix**: Leave as-is (documented intentional limitation).

### P4-003: deepisles.py has unused constants ⚠️ CONFIRMED

**Location**: `deepisles.py:35-36`

```python
EXPECTED_INPUT_FILES = ["dwi.nii.gz", "adc.nii.gz"]
OPTIONAL_INPUT_FILES = ["flair.nii.gz"]
```

These are defined but never used.

**Fix**: Use in `validate_input_folder()` error messages, or remove.

### P4-004: Frontend duplicated retry constants ⚠️ CONFIRMED

**Location**: `useSegmentation.ts:9-11` + `CaseSelector.tsx:5-7`

Both files define:
```typescript
const MAX_COLD_START_RETRIES = 5;
const INITIAL_RETRY_DELAY = 2000;
const MAX_RETRY_DELAY = 30000;
```

**Fix**: Extract to shared `frontend/src/utils/retry.ts`.

---

## Architecture Violations Check ✅ PASSED

The external audit confirmed NO architecture violations:
- No API importing/calling Gradio/UI code
- Clear React SPA / FastAPI backend separation
- Strong path traversal defenses in file serving
- Safe job-id handling and cleanup

---

## Fix Priority Order

1. **P0-001**: Docker build crash (release blocker)
2. **P1-001, P1-002**: Makefile + stale comment
3. **P2-001 through P2-005**: Wire in dead config settings
4. **P2-006, P2-007**: Dataset caching
5. **P2-008 through P2-010**: Security hardening
6. **P3-***: Documentation updates
7. **P4-***: Code cleanliness

---

## Implementation Notes

Per user directive: **Wire settings in properly rather than removing dead config.**
These settings were created for a reason - they should work as documented.
