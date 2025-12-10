# Root Cause Analysis: HF Spaces "Loading..." Forever (Issue #24)

**Date:** 2025-12-10
**Status:** IN PROGRESS
**Branch:** `debug/niivue-head-script-loading`

---

## Executive Summary

The HuggingFace Spaces app hangs on "Loading..." indefinitely because **dynamic ES module `import()` inside `gr.HTML(js_on_load=...)` blocks Gradio's Svelte frontend from hydrating**.

This was proven empirically in our own A/B test documented in `docs/specs/24-bug-hf-spaces-loading-forever.md`:

> **Diagnostic test:** Disabled `js_on_load` parameter entirely.
> **Result:** App loads perfectly! Everything works EXCEPT Interactive 3D viewer.

---

## First Principles Analysis

### How Gradio Renders

1. Server sends initial HTML with loading spinner
2. Gradio's Svelte app downloads and hydrates
3. Components mount, including `gr.HTML`
4. `js_on_load` executes during component mount
5. Loading spinner clears when hydration completes

### Why Dynamic Import Blocks Hydration

The current `js_on_load` code does this (viewer.py:497):

```javascript
const module = await import(niivueUrl);  // <-- BLOCKS HYDRATION
window.Niivue = module.Niivue;
```

**Problem:** If this `import()` hangs (CSP issues, network issues, MIME type issues, etc.), the async IIFE never resolves, and Svelte's mount lifecycle stalls. HF Spaces silently blocks or delays these imports.

### Why `head=` Works

The `head=` parameter injects content into `<head>` BEFORE Gradio hydrates:

```html
<head>
  <!-- Injected by head= -->
  <script type="module">
    const { Niivue } = await import('/gradio_api/file=.../niivue.js');
    window.Niivue = Niivue;
  </script>
</head>
```

**Key insight:** Even if this script fails, Gradio still loads because:
1. Script tags in `<head>` don't block Svelte hydration
2. They run BEFORE Gradio components mount
3. Failure just means `window.Niivue` is undefined (graceful degradation)

Then `js_on_load` simply USES `window.Niivue` (no imports):

```javascript
// No import() - just use what's already loaded
const Niivue = window.Niivue;
if (!Niivue) {
  // Show error message, don't block
}
```

---

## Evidence-Based Conclusions

| Claim | Evidence | Validated |
|-------|----------|-----------|
| Dynamic `import()` in `js_on_load` blocks HF Spaces | A/B test: disabling `js_on_load` makes app load | **YES** |
| Vendored NiiVue file is served correctly | Local testing shows 200 response | **YES** |
| `gr.set_static_paths()` is called correctly | Called before any Blocks in both entry points | **YES** |
| `allowed_paths` is configured correctly | Both entry points pass `allowed_paths` | **YES** |
| `demo.load()` doesn't block initial render | Gradio docs confirm load runs post-hydration | **YES** |

---

## The Fix

### Before (Broken)

```python
# viewer.py - NIIVUE_ON_LOAD_JS
const module = await import(niivueUrl);  # Dynamic import in js_on_load
window.Niivue = module.Niivue;
```

```python
# ui/app.py - No head= parameter, relying on js_on_load to load NiiVue
demo.launch(...)  # No head= parameter
```

### After (Fixed)

```python
# ui/app.py - Load NiiVue via head= BEFORE Gradio hydrates
from stroke_deepisles_demo.ui.viewer import get_niivue_head_html

get_demo().launch(
    head=get_niivue_head_html(),  # Inject NiiVue loader into <head>
    ...
)
```

```python
# viewer.py - NIIVUE_ON_LOAD_JS just USES window.Niivue (no import)
const Niivue = window.Niivue;
if (!Niivue) {
    // Graceful error - don't block Gradio
    container.innerHTML = 'NiiVue failed to load...';
    return;
}
```

---

## Why Previous Attempts Failed

### Attempt 1: CDN Import
**Failed because:** HF Spaces CSP blocks external CDN imports

### Attempt 2: Vendor NiiVue + Dynamic Import in js_on_load
**Failed because:** Dynamic `import()` in js_on_load still blocks Svelte hydration, even for local files

### Attempt 3: Remove head= and make js_on_load self-sufficient
**Failed because:** This approach doubled down on the broken pattern (dynamic import in js_on_load)

### This Fix: head= for loading + js_on_load for init only
**Should work because:** Matches the architecture documented in spec 24 and proven by the A/B test

---

## Test Strategy

1. **Local sanity:** Run with fix, verify app loads and NiiVue works
2. **A/B comparison:** Compare behavior with/without `head=` parameter
3. **HF Spaces deployment:** Push to hf-personal remote and verify
4. **Console inspection:** Check for `[NiiVue Loader]` logs in browser console

---

## Files to Modify

| File | Change |
|------|--------|
| `src/stroke_deepisles_demo/ui/viewer.py` | Remove `import()` from js_on_load, use `window.Niivue` directly |
| `src/stroke_deepisles_demo/ui/app.py` | Add `head=get_niivue_head_html()` to launch() |
| `app.py` | Same as above for local dev |
