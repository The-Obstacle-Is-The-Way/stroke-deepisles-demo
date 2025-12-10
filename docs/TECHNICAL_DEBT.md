# Technical Debt and Known Issues

> **Last Audit**: December 2025 (Revision 6)
> **Auditor**: Claude Code + External Senior Review
> **Status**: P0 BLOCKER - NiiVue/WebGL integration broken on HF Spaces

## Summary

**CRITICAL ISSUE**: The NiiVue 3D viewer does not work on HuggingFace Spaces due to Gradio architecture limitations. See Issue #24.

| Severity | Count | Description | Status |
|----------|-------|-------------|--------|
| **P0 (Critical)** | 1 | NiiVue/WebGL on HF Spaces | **BLOCKED** |
| P2 (Medium) | 0 | Temp dir leak, silent empty dataset, brittle git dep | **All Fixed** |
| P3 (Low) | 0 | SSRF vector, float64 memory, base64 overhead | **All Fixed** |
| P3 (Low) | 1 | Type ignores | **Acceptable** |

---

## P0 BLOCKER: NiiVue/WebGL on HuggingFace Spaces (Issue #24)

### Problem

The Interactive 3D Viewer (NiiVue) causes the entire HF Spaces app to hang on "Loading..." forever.

### Root Cause

**Gradio does not natively support custom WebGL content.** All hack attempts have **FAILED** (confirmed Dec 10, 2025):

| Attempt | Date | Result |
|---------|------|--------|
| CDN import in js_on_load | Dec 9 | FAILED - CSP blocked |
| Vendored + import() in js_on_load | Dec 9 | FAILED - Blocks Svelte hydration |
| head_paths with loader HTML | Dec 9 | FAILED - Same issue |
| head= with inline import() | Dec 10 | **FAILED** - Confirmed DOA |

Gradio maintainers explicitly closed Issues #4511 (NIfTI support) and #7649 (WebGL canvas) as "not planned", recommending Custom Components instead.

**There is no gr.HTML hack that works. The only path forward is a Gradio Custom Component.**

### Solution

Build a **Gradio Custom Component** that properly wraps NiiVue using Svelte.

See: `docs/specs/28-gradio-custom-component-niivue.md`

### Workaround (Current)

The "Static Report" tab (Matplotlib 2D slices) works correctly. Only the "Interactive 3D" tab is broken.

---

## Resolved Issues (Fixed in `fix/technical-debt`)

### ✅ P2: Silent Empty Dataset on Missing Data Directory
**Resolution**: Updated `adapter.py` to raise `FileNotFoundError` with clear message. verified with `tests/data/test_adapter_edge_cases.py`.

### ✅ P2: Unbounded Temporary Directory Accumulation
**Resolution**: Updated `pipeline.py` to default `cleanup_staging=True`. Updated `app.py` to explicitly request cleanup. Verified with `tests/test_pipeline_cleanup.py`.

### ✅ P2: Brittle Git Branch Dependency
**Resolution**: Pinned `datasets` dependency in `pyproject.toml` to specific commit hash (`c1c15aa`) ensuring immutability.

### ✅ P3: Latent SSRF Vector
**Resolution**: Removed unreachable HTTP download code from `staging.py`. Verified with `tests/data/test_staging_security.py`.

### ✅ P3: Redundant float64 Cast (Memory Optimization)
**Resolution**: Updated `metrics.py` to load NIfTI data as `float32` directly, reducing memory usage by 50%. Type annotations updated to use `np.floating[Any]` for flexibility. Verified with `tests/test_metrics_memory.py`.

### ✅ P3: Base64 Data URL Overhead for NiiVue Viewer (Issue #19)
**Resolution**: Replaced base64 data URLs (~65MB payloads) with Gradio's built-in file serving via `/gradio_api/file=` URLs. Benefits:
- **33% smaller payloads** (no base64 encoding overhead)
- **Reduced browser memory pressure** (streaming vs. DOM string storage)
- **Faster load times** (browser can efficiently fetch files)

Implementation:
- Added `nifti_to_gradio_url()` function in `viewer.py`
- Removed deprecated `nifti_to_data_url()` function
- Updated `app.py` to use Gradio file serving
- Verified with `tests/ui/test_viewer.py::TestNiftiToGradioUrl`

See: `docs/specs/19-perf-base64-to-file-urls.md`

---

## Remaining Acceptable Limitations

### P3: Type Ignore Comments
**Status**: Industry-standard workarounds for libraries with incomplete type stubs (`nibabel`, `numpy`, `gradio`). No action required.

---

## Conclusion

The codebase is **production-ready for all features EXCEPT the Interactive 3D Viewer (NiiVue)**. All other technical debt items are resolved.

**Next step:** Implement Gradio Custom Component per spec #28 to fix the P0 blocker.
