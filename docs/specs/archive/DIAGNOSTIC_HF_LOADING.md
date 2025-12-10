# Diagnostic: HuggingFace Spaces "Loading..." Forever Bug

**Date**: 2025-12-10
**Status**: UNRESOLVED - App stuck on "Loading..." despite backend running
**Symptom**: HF Spaces shows "Running on T4", logs show successful startup, but UI never renders

## Observed Behavior

```
===== Application Startup at 2025-12-10 02:10:47 =====
* Running on local URL:  http://0.0.0.0:7860
```

- Backend Python starts successfully
- Gradio server binds to `0.0.0.0:7860` (correct for Docker)
- Frontend shows Gradio "Loading..." spinner indefinitely
- No error messages in container logs

---

## Research Findings

### 1. Known Gradio Issues with Custom JavaScript

#### Issue #11649: Custom JS via `head` fails with 404
**Source**: [GitHub Issue #11649](https://github.com/gradio-app/gradio/issues/11649)

Users report custom JavaScript files failing to load even with `allowed_paths` configured.

**Solution found**: Use `head_paths` parameter instead of `head`:
```python
with gr.Blocks(head_paths=["custom.html"]) as demo:
```

Alternative URL format that works: `/gradio_api/file=static/custom.js` instead of `/file/static/custom.js`

#### Issue #10250: JavaScript in `head` param not executing
**Source**: [GitHub Issue #10250](https://github.com/gradio-app/gradio/issues/10250)

JavaScript occasionally executes after extended delays (5-10+ minutes) or not at all.

**Key insight**: `gr.HTML()` components intentionally do NOT execute JavaScript for security. Only `head` parameter supports JS execution.

#### Issue #6426: gr.Blocks head argument not working
**Source**: [GitHub Issue #6426](https://github.com/gradio-app/gradio/issues/6426)

Two critical bugs:
1. Only the FIRST script tag from `head` is applied
2. Script tags are injected AFTER page loads, preventing execution

**Fixed in PR #6639** - but may require specific Gradio version.

### 2. ES Module Script Behavior

**Source**: [ES Modules Explainer](https://gist.github.com/jakub-g/385ee6b41085303a53ad92c7c8afd7a6)

Key facts about `<script type="module">`:
- **Always deferred by default** - does NOT block HTML parsing
- **No way to make it blocking** - even without async/defer
- If import fails, script silently fails but shouldn't block page

**Implication**: Our NiiVue loader (`<script type="module">`) should NOT be blocking Gradio's rendering. The issue is elsewhere.

### 3. HuggingFace Spaces Known Issues

#### Origin Mismatch Bug (Issue #10893)
**Source**: [HF Forum Thread](https://discuss.huggingface.co/t/gradio-space-javascript-not-executing-fields-not-populating-persistent-syntaxerror-in-browser-console/163689)

Gradio's `postMessage` calls fail due to origin mismatch between `https://huggingface.co` and the actual Space URL. This can prevent JavaScript execution entirely.

#### Docker "Running" But "Loading..." Forever
**Source**: [HF Forum Thread](https://discuss.huggingface.co/t/space-stuck-in-building-despite-gradio-welcome-port/36890)

Common causes:
- Binding to `127.0.0.1` instead of `0.0.0.0` (**we already fixed this**)
- Incorrect port configuration (**we use 7860**)
- Private Space authentication issues (**our Space is public**)

#### Interface Not Showing Despite Running
**Source**: [HF Forum Thread](https://discuss.huggingface.co/t/bug-free-gradio-interface-not-loading-on-hfs/25102)

Assigning Interface to a variable before launching can cause this:
```python
# WRONG
iface = gr.Interface(...).launch()

# RIGHT
gr.Interface(...).launch()
```

**Our code**: We use `get_demo().launch()` which SHOULD be correct.

### 4. Gradio set_static_paths Requirements

**Source**: [Gradio Docs](https://www.gradio.app/docs/gradio/set_static_paths)

- Must be called BEFORE creating Blocks
- Affects ALL Gradio apps in the same interpreter session
- Exposes entire directories to network (security consideration)

**Our code**: We call `gr.set_static_paths()` at module level before imports. ✅

### 5. Browser Cache Issues

**Source**: [HF Forum Thread](https://discuss.huggingface.co/t/issue-with-perpetual-loading-on-the-space/35684)

Some "Loading..." issues resolved by clearing browser cache. Works in one browser but not another.

**Unlikely cause**: This is a fresh deployment, not a cache issue.

---

## Our Current Implementation

### JavaScript Loading Flow

1. `app.py` (root entry point for HF Spaces Docker):
   - Calls `gr.set_static_paths(paths=[str(_ASSETS_DIR)])` before imports
   - Imports `get_demo()` and `get_niivue_loader_path()`
   - Launches with `head_paths=[str(niivue_loader)]`

2. `ui/app.py` (also calls set_static_paths):
   - Module-level `gr.set_static_paths()` before imports
   - Creates demo with `js_on_load=NIIVUE_ON_LOAD_JS` on gr.HTML component

3. `viewer.py`:
   - Generates `niivue-loader.html` at runtime with absolute path
   - Content: `<script type="module">import { Niivue } from '/gradio_api/file=...'</script>`

### Files Involved

| File | Purpose | Status |
|------|---------|--------|
| `app.py` (root) | HF Spaces entry point | Uses head_paths ✅ |
| `src/.../ui/app.py` | Main UI module | Uses js_on_load ✅ |
| `src/.../ui/viewer.py` | NiiVue loader generation | Generates at runtime ✅ |
| `src/.../ui/components.py` | UI components | Uses NIIVUE_ON_LOAD_JS ✅ |
| `src/.../ui/assets/niivue.js` | Vendored NiiVue library | 2.9MB, tracked ✅ |
| `src/.../ui/assets/niivue-loader.html` | Generated loader | gitignored ✅ |

### Dockerfile CMD

```dockerfile
CMD ["python", "-m", "stroke_deepisles_demo.ui.app"]
```

This runs `ui/app.py` as `__main__`, which should execute our launch() with head_paths.

---

## Hypotheses

### H1: `js_on_load` Breaking Gradio Initialization

**Theory**: The `js_on_load` parameter on `gr.HTML` might be executing before Gradio fully initializes, causing a crash.

**Evidence**: Our code has `js_on_load=NIIVUE_ON_LOAD_JS` which is a complex async IIFE.

**Test**: Remove `js_on_load` parameter and see if app loads.

### H2: `head_paths` Not Being Applied on HF Spaces

**Theory**: The `head_paths` parameter might not be reaching the frontend on HF Spaces due to Docker networking or Gradio configuration.

**Evidence**: Issue #11649 shows head-related parameters have bugs.

**Test**: Check browser Network tab for niivue.js 404 or missing script.

### H3: demo.load() Blocking Initial Render

**Theory**: The `demo.load(initialize_case_selector, ...)` call might be blocking the initial UI render.

**Evidence**: `initialize_case_selector()` calls `list_case_ids()` which loads HuggingFace dataset.

**Test**: Remove demo.load() and see if app loads.

### H4: Double set_static_paths Causing Conflict

**Theory**: Both `app.py` (root) and `ui/app.py` call `gr.set_static_paths()`. This might cause conflicts.

**Evidence**: Gradio docs say "affects ALL Gradio apps in same interpreter session".

**Test**: Remove one of the set_static_paths calls.

### H5: Module Import Order Issue

**Theory**: The order of imports and set_static_paths calls might matter on HF Spaces but not locally.

**Evidence**: We have `noqa: E402` comments indicating non-standard import order.

**Test**: Trace exact import order and when set_static_paths is effective.

### H6: Path Resolution Different in Docker

**Theory**: `Path(__file__).resolve()` might resolve to different paths in Docker vs local.

**Evidence**: We use absolute paths for NIIVUE_JS_URL computed at import time.

**Test**: Log the actual paths being computed in Docker.

---

## Diagnostic Steps to Try

1. **Minimal Test**: Create a branch that removes ALL custom JS and test if basic Gradio loads
2. **Log Paths**: Add logging to show exactly what paths are computed in Docker
3. **Browser DevTools**: Check Network tab and Console for errors (if accessible)
4. **Gradio Version**: Verify we're using a version with all relevant fixes
5. **HF Spaces Logs**: Check full container logs for any Python errors not shown in UI

---

## Related Documentation

- [AUDIT_JS_LOADING_ISSUES.md](./AUDIT_JS_LOADING_ISSUES.md) - Previous audit of JavaScript loading issues
- [docs/specs/24-bug-hf-spaces-loading-forever.md](./docs/specs/24-bug-hf-spaces-loading-forever.md) - Original bug specification

---

## External Resources

- [Gradio Custom CSS and JS Guide](https://www.gradio.app/guides/custom-CSS-and-JS)
- [Gradio File Access Guide](https://www.gradio.app/guides/file-access)
- [Gradio set_static_paths Docs](https://www.gradio.app/docs/gradio/set_static_paths)
- [Gradio Issue #11649](https://github.com/gradio-app/gradio/issues/11649) - head_paths solution
- [Gradio Issue #10250](https://github.com/gradio-app/gradio/issues/10250) - head JS not executing
- [Gradio Issue #6426](https://github.com/gradio-app/gradio/issues/6426) - head argument bugs
- [HF Spaces Docker Guide](https://huggingface.co/docs/hub/spaces-sdks-docker)
