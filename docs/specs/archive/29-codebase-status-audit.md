# Spec #29: Codebase Status Audit (Issue #24 NiiVue/WebGL)

**Date:** 2025-12-10
**Status:** ALL `gr.HTML` HACKS CONFIRMED FAILED (Dec 10, 2025)
**Purpose:** Top-down analysis of current frontend/NiiVue implementation state after multiple hotfix attempts

---

## Executive Summary: The `gr.HTML` + `js_on_load` + `import()` Pattern is Broken

After 6 iterations of attempted hotfixes for Issue #24 (HF Spaces "Loading..." forever), **every `gr.HTML`-based approach has failed**:

| Attempt | Result |
|---------|--------|
| CDN import | FAILED - CSP blocked |
| Vendored + js_on_load import() | FAILED - Blocks Svelte hydration |
| head_paths | FAILED - Same hydration issue |
| head= with import() | **FAILED** - Confirmed Dec 10 |

**Root Cause (PROVEN):** Async `import()` inside `js_on_load` blocks Gradio's Svelte hydration. Our A/B test confirmed: disabling `js_on_load` makes the app load.

**Clarification:** Gradio CAN do WebGL via Custom Components (`gradio-litmodel3d` proves this). The issue is the `gr.HTML` approach, not Gradio itself.

**The correct solution is Gradio Custom Component (spec #28).**

---

## Current Frontend Architecture

### File Inventory

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `ui/viewer.py` | NiiVue HTML/JS generation | 643 | **BLOATED** - contains 5 approaches |
| `ui/app.py` | Main Gradio app | 313 | Clean |
| `ui/components.py` | UI components | 94 | Clean |
| `app.py` (root) | Local dev entry | 61 | Clean |
| `ui/assets/niivue.js` | Vendored NiiVue v0.65.0 | 2.9MB | **NECESSARY** |

### What's in `viewer.py` Right Now

| Component | Lines | Status | Notes |
|-----------|-------|--------|-------|
| `NIIVUE_VERSION` | 30 | OK | Version tracking |
| `_ASSET_DIR`, `_NIIVUE_JS_PATH` | 31-32 | OK | Path constants |
| `NIIVUE_JS_URL` | 36 | **UNUSED** | Computed but not actually used |
| Module-level logging | 39-42 | **SLOP** | 4 log statements at import time |
| `get_niivue_head_html()` | 45-77 | **PROBLEMATIC** | Still uses `await import()` |
| `get_niivue_loader_path()` | 80-109 | **DEPRECATED** | Marked deprecated but still exists |
| `nifti_to_gradio_url()` | 112-142 | OK | Issue #19 fix, working |
| `get_slice_at_max_lesion()` | 145-187 | OK | Matplotlib helper |
| `render_3panel_view()` | 190-281 | OK | Matplotlib 3-panel |
| `render_slice_comparison()` | 284-380 | OK | Matplotlib comparison |
| `create_niivue_html()` | 383-434 | OK | HTML generation |
| `NIIVUE_ON_LOAD_JS` | 449-538 | **MOSTLY OK** | No import(), uses window.Niivue |
| `NIIVUE_UPDATE_JS` | 546-642 | **MOSTLY OK** | No import(), uses window.Niivue |

---

## The Core Problem: `get_niivue_head_html()` Still Uses `import()`

The current "fix" in `get_niivue_head_html()` does this:

```javascript
// viewer.py:63-76
<script type="module">
    try {
        const niivueUrl = '{NIIVUE_JS_URL}';
        console.log('[NiiVue Loader] Attempting to load from:', niivueUrl);
        const { Niivue } = await import(niivueUrl);  // <-- SAME BROKEN PATTERN!
        window.Niivue = Niivue;
        console.log('[NiiVue Loader] Successfully loaded');
    } catch (error) {
        console.error('[NiiVue Loader] FAILED to load:', error);
        window.NIIVUE_LOAD_ERROR = error.message;
    }
</script>
```

**This is the EXACT same `await import()` pattern that breaks on HF Spaces.**

The only difference from our previous attempts:
- Before: `await import()` in `js_on_load`
- Now: `await import()` in `head=` script

**Why this might not matter:** The A/B test proved that `js_on_load` with async code breaks Gradio. Moving the `import()` to `head=` might help, but it's still executing async code that could fail silently and leave `window.Niivue` undefined.

---

## What's Necessary vs What's Slop

### NECESSARY (Keep)

| Item | Why |
|------|-----|
| `ui/assets/niivue.js` | HF Spaces CSP blocks CDN imports |
| `gr.set_static_paths()` | Required for Gradio 6.x file serving |
| `nifti_to_gradio_url()` | Issue #19 fix, working |
| `create_niivue_html()` | Generates viewer HTML |
| `NIIVUE_ON_LOAD_JS` | Initializes viewer (doesn't import) |
| `NIIVUE_UPDATE_JS` | Re-initializes after updates |
| Matplotlib functions | Working 2D fallback |
| `allowed_paths` in launch() | Runtime file access |

### SLOP (Should Remove/Refactor)

| Item | Why It's Slop |
|------|---------------|
| `NIIVUE_JS_URL` module-level computation | Computed but unused in production |
| Module-level logging (lines 39-42) | Noisy startup logs, not useful |
| `get_niivue_loader_path()` | Deprecated, generates file we don't need |
| `get_niivue_head_html()` with import() | Still uses broken pattern |
| Multiple diagnostic docs | Overlapping, contradictory, stale |

### UNCERTAIN (Depends on head= fix working)

| Item | Status |
|------|--------|
| `head=get_niivue_head_html()` in launch() | **30% chance this works** |

---

## Documentation Status

### docs/specs/ Files

| File | Status | Issue |
|------|--------|-------|
| `00-context.md` | **ACCURATE** | None |
| `28-gradio-custom-component-niivue.md` | **ACCURATE** | Just written |
| `AUDIT_JS_LOADING_ISSUES.md` | **OUTDATED** | Says `set_static_paths` is blocker, but we've moved past that |
| `DIAGNOSTIC_HF_LOADING.md` | **OUTDATED** | Lists hypotheses we've since disproven |
| `ROOT_CAUSE_ANALYSIS.md` | **PARTIALLY OUTDATED** | Says "IN PROGRESS", discusses head= as solution |
| `GRADIO_WEBGL_ANALYSIS.md` | **ACCURATE** | Core analysis, identifies real problem |

### docs/TECHNICAL_DEBT.md

| Status | Issue |
|--------|-------|
| **OUTDATED** | Claims "Ironclad/Production-Ready" but doesn't mention P0 NiiVue/WebGL blocker |

---

## Recommended Cleanup Actions

### Immediate (If head= fix fails)

1. **Delete deprecated code:**
   - Remove `get_niivue_loader_path()`
   - Remove module-level logging
   - Clean up `NIIVUE_JS_URL` if unused

2. **Archive old diagnostic docs:**
   - Move `AUDIT_JS_LOADING_ISSUES.md` to `archive/`
   - Move `DIAGNOSTIC_HF_LOADING.md` to `archive/`
   - Update `ROOT_CAUSE_ANALYSIS.md` status

3. **Update TECHNICAL_DEBT.md:**
   - Add P0 section for NiiVue/WebGL blocker
   - Link to spec #28 (Custom Component)

### Long-term (After decision on path forward)

1. **If Custom Component route:**
   - Remove all `head=` NiiVue loading code
   - Remove `get_niivue_head_html()`
   - Simplify `viewer.py` to just Matplotlib functions
   - NiiVue loading becomes the component's responsibility

2. **If 2D fallback route:**
   - Remove entire NiiVue integration
   - Remove `ui/assets/niivue.js` (2.9MB)
   - Remove `NIIVUE_ON_LOAD_JS`, `NIIVUE_UPDATE_JS`
   - Keep only Matplotlib rendering

---

## Honest Assessment

### What We've Tried (6+ iterations)

1. **CDN import** → Blocked by CSP
2. **Vendored + dynamic import in js_on_load** → Blocks Svelte hydration
3. **head_paths with loader HTML** → Complex, didn't work
4. **head= with inline import()** → Current state, **probably won't work**
5. **Various set_static_paths/allowed_paths combos** → File serving works, JS loading doesn't

### The Pattern

Every attempt has been a variation of:
> "Load NiiVue via some JavaScript mechanism within Gradio"

Every attempt has failed because:
> **Gradio was not designed for custom WebGL content**

### The Correct Solution

**Stop fighting Gradio's architecture. Use a Gradio Custom Component.**

This is:
- What Gradio maintainers recommend (Issues #4511, #7649)
- How existing WebGL components work (gradio-litmodel3d)
- 90% success probability vs 30% for more hacks

See spec #28 for implementation details.

---

## Current Entry Point Flow

```
HF Spaces Docker
    ↓
CMD ["python", "-m", "stroke_deepisles_demo.ui.app"]
    ↓
ui/app.py __main__ block
    ↓
gr.set_static_paths([_ASSETS_DIR])  # Enable file serving
    ↓
get_demo()  # Creates Blocks with js_on_load components
    ↓
demo.launch(
    head=get_niivue_head_html(),    # <-- Injects <script type="module"> with import()
    allowed_paths=[_ASSETS_DIR],
)
    ↓
Browser loads page
    ↓
<head> script runs: await import('/gradio_api/file=.../niivue.js')
    ↓
[UNCERTAIN] Does import() succeed? Does it block Svelte?
    ↓
If yes: window.Niivue is set, js_on_load works
If no: window.Niivue undefined, viewer shows error
```

---

## Files Modified During Issue #24 Debug

| File | Changes | Commits |
|------|---------|---------|
| `viewer.py` | ~6 rewrites of JS loading approach | Multiple |
| `ui/app.py` | Added head=, set_static_paths | Multiple |
| `app.py` | Same as ui/app.py | Multiple |
| `ui/assets/niivue.js` | Added vendored library | 1 |
| `.gitignore` | Added niivue-loader.html | 1 |
| `.pre-commit-config.yaml` | Exclude assets/ from large file check | 1 |

---

## Conclusion

**The codebase is messy but not unfixable.** The mess comes from iterating through multiple failed approaches without cleaning up between attempts.

**The real issue is architectural:** Gradio + custom WebGL = unsupported pattern.

**Next steps:**
1. Test if current `head=` approach works on HF Spaces (low confidence)
2. If it fails, implement Gradio Custom Component (spec #28)
3. Clean up cruft regardless of which path we take

---

## Appendix: How to Verify Current State

```bash
# Check if NiiVue file serving works
curl -I "https://[space-url]/gradio_api/file=/home/user/demo/src/stroke_deepisles_demo/ui/assets/niivue.js"
# Should return 200 OK with application/javascript

# Check browser console for:
# - "[NiiVue Loader] Attempting to load from: ..."
# - "[NiiVue Loader] Successfully loaded" OR "[NiiVue Loader] FAILED"
# - Any errors during Gradio initialization
```
