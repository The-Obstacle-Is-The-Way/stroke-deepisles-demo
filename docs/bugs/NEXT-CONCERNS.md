# Next Concerns - Config Audit & Fixes Complete

**Date:** 2025-12-13
**Branch:** `fix/remaining-audit-issues`
**Status:** IMPLEMENTED - Ready for review

---

## Summary of Changes

### P1 Fixes (Safety Critical)

| Issue | Fix | File |
|-------|-----|------|
| max_concurrent_jobs=10 unsafe | Changed default to 1 | `config.py:97-98` |
| Timeout not passed to direct invocation | Added timeout parameter | `deepisles.py:222-223, 318` |

### Slop Removed (Never Actually Needed)

| Setting | Reason | Status |
|---------|--------|--------|
| `hf_cache_dir` | Duplicates `HF_HOME` (already set in Dockerfile) | **REMOVED** |
| `temp_dir` | Duplicates `TMPDIR` (Python native) | **REMOVED** |
| `deepisles_repo_path` | No valid use case (direct mode only in container) | **REMOVED** |
| `DEEPISLES_PATH` env var | Unused in direct.py | **REMOVED** from Dockerfile |

### P2 Fixes

| Issue | Fix | File |
|-------|-----|------|
| Concurrency check after expensive validation | Added pre-check before list_case_ids() | `routes.py:95-101` |
| Direct invocation logs verbose at INFO | Changed to DEBUG | `direct.py:200-206` |
| FastAPI doesn't apply log settings | Added setup_logging() at startup | `main.py:47-48` |

### P3/P4 Cleanup

| Issue | Fix | File |
|-------|-----|------|
| Package description mentions Gradio | Updated to React SPA + FastAPI | `__init__.py:1` |
| HEAD comment wrong (should be OPTIONS) | Fixed comment | `main.py:112` |
| Configuration docs outdated | Completely rewritten | `docs/guides/configuration.md` |

---

## Test Results

```text
157 passed, 7 deselected in 12.73s
ruff check: All checks passed!
ruff format: 27 files already formatted
mypy: Success: no issues found in 27 source files
```

---

## Files Changed

1. `src/stroke_deepisles_demo/core/config.py` - Removed slop, fixed max_concurrent_jobs
2. `src/stroke_deepisles_demo/inference/deepisles.py` - Pass timeout to direct invocation
3. `src/stroke_deepisles_demo/inference/direct.py` - DEBUG logging for verbose output
4. `src/stroke_deepisles_demo/api/routes.py` - Pre-check concurrency before validation
5. `src/stroke_deepisles_demo/api/main.py` - setup_logging() at startup, fix OPTIONS comment
6. `src/stroke_deepisles_demo/__init__.py` - Updated package description
7. `Dockerfile` - Removed unused DEEPISLES_PATH env var
8. `docs/guides/configuration.md` - Complete rewrite with current settings

---

## What's Left (P4 - Optional)

These are exported in public API, so removing could be breaking change. Left as-is:
- `DatasetInfo` class (defined but never instantiated)
- `create_staging_directory` (has tests, is a utility function)

These are minor doc issues, not affecting functionality:
- Broken references to archived spec docs in some files
