# Issue #32: HF Spaces UI Frozen After All Fixes - Deep Audit

**Date:** 2025-12-10
**Status:** INVESTIGATION IN PROGRESS
**SSOT:** This document

---

## Executive Summary

After applying all fixes from PRs #29, #30, #31 (custom component, Docker build, gradio prop),
the HF Spaces UI remains COMPLETELY FROZEN:
- Dropdown shows "Initializing dataset... please wait" (never updates)
- NiiVue shows "loading ..." (default when no volumes)
- Buttons don't respond
- Nothing is interactive

This document contains a comprehensive audit of all potential causes.

---

## Symptoms

| Symptom | What It Means |
|---------|---------------|
| Dropdown shows initial state | `demo.load()` callback NEVER completed |
| NiiVue shows "loading ..." | Normal - NiiVue's default text when no volumes loaded |
| StatusTracker shows "Loading..." | Loading state is set but never cleared |
| Buttons don't respond | Event handlers not connected OR events blocked |

---

## Verified NOT Causes

| Factor | Evidence | Status |
|--------|----------|--------|
| Python data loading slow | Tested: 0.33s total (instant) | **RULED OUT** |
| Missing `gradio` prop | PR #31 added it correctly | **RULED OUT** |
| Missing `i18n`/`autoscroll` | PR #31 passes them to StatusTracker | **RULED OUT** |
| Templates not in git | Verified: all 8 template files tracked | **RULED OUT** |
| Templates not on HF remote | Verified: commit 491d824 has all files | **RULED OUT** |
| Dockerfile missing packages/ | PR #30 fixed this | **RULED OUT** |
| Wrong server binding | config.py has `server_name: str = "0.0.0.0"` | **RULED OUT** |

---

## Potential Causes (Under Investigation)

### P1: Custom Component Blocks Gradio Event System

**Evidence from Web Research:**

1. [GitHub Issue #7026](https://github.com/gradio-app/gradio/issues/7026): Custom component 404 for `style.css` causes "frontend hangs on the loading screen"

2. [GitHub Issue #6087](https://github.com/gradio-app/gradio/issues/6087): Custom components can break on JS imports, causing "dev server gets stuck on the loading screen"

3. [GitHub Issue #9610](https://github.com/gradio-app/gradio/issues/9610): Build completed but component not working - complex templates have untested edge cases

**Hypothesis:**
The NiiVueViewer component's JavaScript initialization might be throwing an error that:
1. Doesn't crash the page (so UI renders)
2. But blocks Gradio's event queue/SSE connection from establishing

**Key Question:**
Does NiiVue's WebGL initialization fail on HF Spaces Docker environment?

### P2: Gradio Queue/SSE Connection Issues

**Evidence from Web Research:**

1. [GitHub Issue #5974](https://github.com/gradio-app/gradio/issues/5974): "Stuck in processing forever when using queue()"

2. [GitHub Issue #4279](https://github.com/gradio-app/gradio/issues/4279): "Stuck On Loading" - new Gradio versions stuck in loading

3. [GitHub Issue #4332](https://github.com/gradio-app/gradio/issues/4332): Loading stuck in non-internet environments

**Hypothesis:**
Gradio's SSE (Server-Sent Events) connection might not be establishing properly, so:
- Initial HTML renders fine
- But events never fire (no queue connection)
- `demo.load()` is registered but never triggers

### P3: WebGL Context Issues in Docker

**Evidence:**
- NiiVue requires WebGL2 for rendering
- Docker containers may not have GPU/graphics drivers
- Safari WebWorker issues with WebGL reported in related libraries

**Hypothesis:**
`nv.attachToCanvas(canvas)` might hang or throw when WebGL2 is unavailable,
and even though we have try/catch, the error might propagate in a way that
affects Gradio's initialization.

### P4: `demo.load()` Return Value Format

**From Gradio Docs:**
> "if your event listener has a single output component, you should **not** return it as a single-item list."

**Current Code:**
```python
def initialize_case_selector() -> gr.Dropdown:
    return gr.Dropdown(
        choices=case_ids,
        value=case_ids[0],
        info="Choose a case from isles24-stroke dataset",
        interactive=True,
    )
```

This should be correct (returns component directly, not in list).
BUT: Missing `label` and `filterable` props could cause issues if Gradio
tries to merge partial updates incorrectly.

---

## Technical Deep Dive

### Custom Component Architecture

```
packages/niivueviewer/
├── backend/
│   └── gradio_niivueviewer/
│       ├── __init__.py
│       ├── niivueviewer.py          # Python component class
│       └── templates/
│           └── component/
│               ├── index.js          # Bundled Svelte component (1.3 MB)
│               ├── style.css         # Component styles (9.3 KB)
│               ├── blosc-D1xNXZJs.js # WASM decoder
│               ├── lz4-1Ws5oVWR.js   # WASM decoder
│               └── zstd-C4EcZnjq.js  # WASM decoder
└── frontend/
    └── Index.svelte                   # Source Svelte component
```

### Key Code Paths

**Index.svelte onMount:**
```typescript
onMount(async () => {
    try {
        nv = new Niivue({...});
        await nv.attachToCanvas(canvas);  // <-- Potential hang point
        initialized = true;
    } catch (error) {
        console.error('[NiiVue] Initialization failed:', error);
        // NOTE: Does NOT re-throw, but initialized stays false
    }
});
```

If `attachToCanvas` hangs (no WebGL), the try/catch won't help - the await
never resolves and Gradio might be waiting for component initialization.

**Gradio Event Registration:**
```python
# In ui/app.py create_app()
demo.load(initialize_case_selector, outputs=[case_selector])
```

This should fire after UI renders. If the custom component blocks render
completion, this might never execute.

---

## Recommended Investigation Steps

### Step 1: Check Browser Console on HF Spaces

Need to inspect browser DevTools console on the HF Spaces page to see:
1. Any JavaScript errors
2. Network tab - are SSE connections establishing?
3. Is `style.css` or `index.js` 404-ing?

### Step 2: Test Without Custom Component

Create a test version that removes NiiVueViewer entirely:
1. Replace `NiiVueViewer` with `gr.Textbox` or `gr.JSON`
2. Deploy to HF Spaces
3. If this works, custom component is definitely the issue

### Step 3: Add Diagnostic Logging to Frontend

Add `console.log` statements to Index.svelte:
```typescript
onMount(async () => {
    console.log('[NiiVue] onMount starting...');
    try {
        console.log('[NiiVue] Creating Niivue instance...');
        nv = new Niivue({...});
        console.log('[NiiVue] Attaching to canvas...');
        await nv.attachToCanvas(canvas);
        console.log('[NiiVue] Attached successfully');
        initialized = true;
    } catch (error) {
        console.error('[NiiVue] Initialization failed:', error);
    }
    console.log('[NiiVue] onMount complete, initialized=', initialized);
});
```

### Step 4: Check if WebGL2 Available

Add WebGL2 detection:
```typescript
onMount(async () => {
    const gl = canvas.getContext('webgl2');
    console.log('[NiiVue] WebGL2 available:', !!gl);
    if (!gl) {
        console.error('[NiiVue] WebGL2 not supported in this environment');
        return;
    }
    // ... rest of initialization
});
```

### Step 5: Verify Gradio Version Compatibility

Check if Gradio 6.x has specific requirements for custom components:
```bash
# In Docker container
pip show gradio  # Check exact version
pip show gradio_niivueviewer  # Check if properly installed
```

---

## Related Issues and Documentation

### Gradio GitHub Issues
- [#7026](https://github.com/gradio-app/gradio/issues/7026): Custom component 404 causes loading hang
- [#6087](https://github.com/gradio-app/gradio/issues/6087): Custom components break on JS import
- [#5974](https://github.com/gradio-app/gradio/issues/5974): Stuck in processing with queue
- [#4279](https://github.com/gradio-app/gradio/issues/4279): Stuck on Loading with new Gradio

### Gradio Documentation
- [Custom Components FAQ](https://www.gradio.app/guides/frequently-asked-questions)
- [HuggingFace Integrations](https://www.gradio.app/guides/using-hugging-face-integrations)

### Previous Audit Documents
- `HF_SPACES_UI_BROKEN_AUDIT.md` - Earlier StatusTracker i18n investigation
- `docs/specs/24-bug-hf-spaces-loading-forever.md` - Original issue spec

---

## Next Actions

1. **IMMEDIATE**: Test without NiiVueViewer component to isolate the issue
2. **DIAGNOSTIC**: Add console.log to frontend and check browser DevTools
3. **FALLBACK**: If custom component is broken, revert to `gr.HTML` approach
4. **LONG-TERM**: Report issue to Gradio team with minimal reproduction

---

## Files Modified

None yet - this is an investigation document.

---

## Revision History

| Date | Change |
|------|--------|
| 2025-12-10 | Initial audit created |
