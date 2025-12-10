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

---

## Update (2025-12-10): Web Research Findings

### Critical Discovery: The Issue is Gradio, NOT HuggingFace Spaces

**Web search confirmed:**
- HF Spaces DOES support JavaScript, WebGL, ES modules
- Working examples: Unity WebGL, Three.js games, Gaussian Splat Viewer
- The issue is specifically **Gradio's handling of custom JavaScript**

**Sources:**
- [HF Unity WebGL Template](https://github.com/huggingface/Unity-WebGL-template-for-Hugging-Face-Spaces)
- [WebGL Gaussian Splat Viewer on HF](https://huggingface.co/spaces/cakewalk/splat)
- [HF Forum: Gradio HTML with JS doesn't work](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)

### Known Gradio Limitations

1. **`gr.HTML()` cannot load `<script>` tags** - They're stripped for security
2. **postMessage origin mismatch bug** (Gradio Issue #10893) - Causes SyntaxError
3. **`js_on_load` with dynamic `import()`** - Can block Svelte hydration

### Alternative Approaches NOT YET TRIED

#### Option 1: `demo.load(_js=...)` with globalThis

```python
scripts = """
async () => {
    const script = document.createElement("script");
    script.src = "/gradio_api/file=.../niivue.js";
    script.type = "module";
    document.head.appendChild(script);
    await new Promise(resolve => script.onload = resolve);
    globalThis.Niivue = window.Niivue;
}
"""
demo.load(None, None, None, _js=scripts)
```

Source: [HF Forum workaround](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)

#### Option 2: `gr.Blocks(js=...)` parameter

```python
with gr.Blocks(js="() => { /* load NiiVue */ }") as demo:
    ...
```

Source: [Gradio Custom CSS/JS Guide](https://www.gradio.app/guides/custom-CSS-and-JS)

#### Option 3: Static HTML Space (Nuclear Option)

If all Gradio approaches fail, create a **Static HTML Space** with pure JS/HTML/CSS.
NiiVue would definitely work since WebGL examples exist on HF Spaces.

Would require rebuilding the UI without Gradio.

### Decision Tree

```
PR #28 (head= approach) works? ──YES──> Done!
        │
        NO
        ↓
Try demo.load(_js=...) works? ──YES──> Done!
        │
        NO
        ↓
Try gr.Blocks(js=...) works? ──YES──> Done!
        │
        NO
        ↓
Static HTML Space (rebuild UI without Gradio)
```
