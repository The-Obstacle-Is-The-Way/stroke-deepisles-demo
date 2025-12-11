# Spec #34: COMPREHENSIVE NiiVue + Gradio Integration Audit

**Date:** 2025-12-10
**Status:** RESEARCH COMPLETE - AWAITING SENIOR REVIEW
**Issue:** #24 (HF Spaces UI Frozen)
**Priority:** P0 - BLOCKING

---

## Executive Summary

This document contains **ALL findings** from exhaustive web research on integrating NiiVue (WebGL medical imaging viewer) with Gradio 6 on HuggingFace Spaces. **No fixes should be attempted until this document is reviewed.**

---

## DEFINITIVE PROOF (2025-12-11 HF Spaces Test)

**Screenshot evidence confirms:**

| Component | Status | Proof |
|-----------|--------|-------|
| Gradio UI | WORKS | App loads, no freeze |
| Dropdown | WORKS | Case selector populated with 149 cases |
| Buttons | WORKS | "Run Segmentation" triggers pipeline |
| Pipeline | WORKS | DeepISLES runs, logs show successful execution |
| NiiVue Viewer | BROKEN | Shows placeholder, script never executed |

**Logs from working deployment:**
```
INFO: Running segmentation for sub-stroke0002
INFO: Downloading case sub-stroke0002 from HuggingFace...
INFO: Case sub-stroke0002 ready: DWI=20.9MB, ADC=12.6MB
INFO: Running DeepISLES via subprocess...
```

**Additional screenshots confirm:**
- Static Report tab works - Matplotlib plots render correctly
- Metrics JSON displays (dice_score, volume_ml, elapsed_seconds)
- Download button works - prediction NIfTI file available
- Only the "Interactive 3D" tab shows placeholder (NiiVue script didn't execute)

**This proves:**
1. **Custom Svelte component WAS the cause** of UI freeze (Issue #24)
2. **gr.HTML with inline `<script>` does NOT work** - script never executes
3. **Everything else in our stack works perfectly** on HF Spaces

**The ONLY remaining issue:** Getting NiiVue to load and render volumes.

---

## Our Stack

```yaml
Python: 3.12
Gradio: >=6.0.0,<7.0.0
Svelte: ^5.43.4  # Used by custom component
@gradio/preview: 0.15.1
@niivue/niivue: 0.65.0
HuggingFace Spaces: Docker SDK
```

---

## PART 1: What We Tried (All Failed on HF Spaces)

### Attempt 1: Custom Svelte Component (`packages/niivueviewer/`)

**Location:** `packages/niivueviewer/frontend/Index.svelte`

**What we built:**
- Full Gradio custom component with Svelte 5
- NiiVue bundled via npm (`@niivue/niivue@0.65.0`)
- StatusTracker for loading states
- Templates compiled via `gradio cc build`

**What failed:**
- PR #29: Missing `gradio` prop for StatusTracker i18n
- PR #30: Missing `packages/` directory in Docker
- PR #31: Added gradio prop, fixed .gitignore
- **Still broken** - UI loads but completely frozen

**Root cause hypothesis:** Unknown. Multiple issues may be compounding.

### Attempt 2: gr.HTML with Inline Script (Current `main` branch)

**Location:** `src/stroke_deepisles_demo/ui/components.py:50-93`

**What we tried:**
```python
return f"""
<div id="niivue-container">
    <canvas id="niivue-canvas"></canvas>
</div>
<script type="module">
(async () => {{
    const {{ Niivue }} = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
    // ... initialization code
}})();
</script>
"""
```

**CRITICAL PROBLEM:** Script tags in gr.HTML **DO NOT EXECUTE**

**Source:** [HuggingFace Forum - radames](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)

> "You can't load scripts via gr.HTML, but you can run a JavaScript function on page load and thus set your JavaScript code to globalThis"

**Why:** When HTML is inserted via innerHTML (which is how gr.HTML works), browsers **do not execute** `<script>` tags. This is a browser security feature, not a Gradio bug.

---

## PART 2: All Researched Approaches

### Approach A: `demo.load(_js=...)` + globalThis

**Source:** [HuggingFace Forum](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316/2)

**How it works:**
```python
scripts = """
async () => {
    const { Niivue } = await import("https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js");
    globalThis.Niivue = Niivue;
    globalThis.initNiivue = async (canvasId, volumes) => {
        const nv = new Niivue({ logging: true });
        await nv.attachToCanvas(document.getElementById(canvasId));
        await nv.loadVolumes(volumes);
        return nv;
    };
}
"""
demo.load(None, None, None, _js=scripts)
```

**Pros:**
- Official workaround from Gradio team
- Scripts execute on page load
- Functions available globally

**Cons:**
- `_js` is technically an internal parameter (not fully documented)
- Need to manually trigger `initNiivue()` when data changes
- No reactive updates

**Verdict:** MAYBE VIABLE - needs testing

### Approach B: `head=` parameter on `launch()`

**Source:** [Gradio Custom CSS and JS Guide](https://www.gradio.app/guides/custom-CSS-and-JS)

**CRITICAL: Gradio 6 Breaking Change**

In Gradio 6, `head=`, `js=`, `css=` moved from `gr.Blocks()` to `launch()`:

```python
# Gradio 5 (OLD - WRONG for us)
with gr.Blocks(head=my_head) as demo:
    ...

# Gradio 6 (NEW - CORRECT)
with gr.Blocks() as demo:
    ...
demo.launch(head=my_head)
```

**Source:** [Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)

**How to use:**
```python
NIIVUE_HEAD = """
<script type="module">
    const { Niivue } = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
    window.Niivue = Niivue;
</script>
"""

with gr.Blocks() as demo:
    ...
demo.launch(head=NIIVUE_HEAD)
```

**Pros:**
- Scripts in `<head>` actually execute
- Loads before Gradio hydrates

**Cons:**
- Only runs once on page load
- Still need mechanism to trigger viewer updates

**Known issue:** [GitHub #11649](https://github.com/gradio-app/gradio/issues/11649) - head= with file paths can cause 404

**Verdict:** PARTIAL SOLUTION - still need update mechanism

### Approach C: `js_on_load` on gr.HTML

**Source:** [Gradio Custom HTML Components Guide](https://www.gradio.app/guides/custom_HTML_components)

**How it works:**
```python
gr.HTML(
    value='<canvas id="nv"></canvas>',
    js_on_load="""
        const canvas = element.querySelector('canvas');
        const nv = new window.Niivue({ logging: true });
        await nv.attachToCanvas(canvas);
        element._niivue = nv;
    """
)
```

**Available variables:**
- `element` - The DOM element
- `props` - Component props including `value`
- `trigger` - Function to trigger Gradio events

**CRITICAL LIMITATION:**
> "Event listeners attached in js_on_load are only attached once when the component is first rendered"

**What this means:**
- `js_on_load` runs ONCE
- When `value` changes (new data), it does NOT re-run
- Cannot dynamically update the viewer

**Verdict:** NOT VIABLE for our use case (need reactive updates)

### Approach D: FastAPI + Raw HTML (Reference Implementation)

**Source:** [TobiasPitters/bids-neuroimaging](https://huggingface.co/spaces/TobiasPitters/bids-neuroimaging)

**Location:** `_reference_repos/bids-neuroimaging/main.py`

**How it works:**
- No Gradio at all
- FastAPI returns raw HTML with inline `<script type="module">`
- NiiVue loaded directly from CDN
- Data fetched via `/initial` and `/next` endpoints

**Why it works:**
- No innerHTML insertion - scripts are in the actual HTML document
- No Gradio event system to fight
- Direct browser execution

**Cons:**
- Lose all Gradio benefits (state, components, themes)
- Have to build everything from scratch

**Verdict:** WORKS but requires abandoning Gradio

### Approach E: gradio-iframe Component

**Source:** [gradio-iframe PyPI](https://pypi.org/project/gradio-iframe/)

**How it works:**
```python
from gradio_iframe import iFrame

with gr.Blocks() as demo:
    viewer = iFrame(value="/static/niivue-viewer.html", height=500)
```

**Pros:**
- Complete isolation from Gradio
- Scripts execute normally in iframe
- Can use postMessage for communication

**Cons:**
- Height issues (known bug)
- Need to maintain separate HTML file
- Two-way communication is complex

**Verdict:** FALLBACK OPTION

---

## PART 3: Known Gradio Issues

### WebGL/3D Related

| Issue | Description | Status |
|-------|-------------|--------|
| [#7649](https://github.com/gradio-app/gradio/issues/7649) | WebGL Canvas component request | Closed - "too niche" |
| [#4511](https://github.com/gradio-app/gradio/issues/4511) | 3D medical image support | Closed - "use custom component" |
| [#5765](https://github.com/gradio-app/gradio/issues/5765) | Model3D rendered see-through | WebGL error |
| [#7632](https://github.com/gradio-app/gradio/issues/7632) | Model3D collapsed in tabs | Open |
| [#7485](https://github.com/gradio-app/gradio/issues/7485) | Model3D not working when embedded | Open |

### Custom Component Related

| Issue | Description | Impact |
|-------|-------------|--------|
| [#7026](https://github.com/gradio-app/gradio/issues/7026) | style.css 404 causes hang | Loading forever |
| [#6087](https://github.com/gradio-app/gradio/issues/6087) | CJS imports break dev server | Dev stuck |
| [#9879](https://github.com/gradio-app/gradio/issues/9879) | Custom components don't work | Templates undefined |
| [#12074](https://github.com/gradio-app/gradio/issues/12074) | Custom components too complex | Proposed gr.Custom |

### JavaScript Loading Related

| Issue | Description | Status |
|-------|-------------|--------|
| [#11649](https://github.com/gradio-app/gradio/issues/11649) | head= with files causes 404 | Closed - use head_paths |
| [#2137](https://github.com/gradio-app/gradio/issues/2137) | User-defined JS support | Closed |
| Forum | gr.HTML scripts don't execute | By design |

---

## PART 4: Our Codebase Problems

### Problem 1: gr.HTML Script Won't Execute

**File:** `src/stroke_deepisles_demo/ui/components.py:50-93`

The current `create_niivue_html()` function returns HTML with `<script type="module">`. **This script will never execute** because:
1. gr.HTML uses innerHTML to insert content
2. Browsers don't execute scripts inserted via innerHTML
3. This is a security feature, not a bug

### Problem 2: Custom Component Still Exists

**Directory:** `packages/niivueviewer/`

The custom Svelte component still exists and is referenced in:
- `pyproject.toml` (as dependency)
- May be imported by HF Spaces build

Even though `components.py` now uses gr.HTML, the custom component presence may cause issues:
- Build time: `gradio cc build` may fail
- Runtime: Conflicting component registrations

### Problem 3: Gradio 6 API Usage

**Files:** `src/stroke_deepisles_demo/ui/app.py`, `app.py`

Currently NOT using any of these Gradio 6 parameters:
- `demo.launch(head=...)`
- `demo.launch(js=...)`
- `demo.load(_js=...)`

The NiiVue library is never loaded into the page.

### Problem 4: No Mechanism for Reactive Updates

Even if we fix script loading, there's no mechanism to:
1. Detect when new data arrives
2. Update the NiiVue viewer with new volumes
3. Re-render without full page refresh

---

## PART 5: Viable Solutions (Ranked)

### Option 1: Head Script + MutationObserver (Recommended)

**Complexity:** Medium
**Risk:** Medium

**How it works:**
1. Load NiiVue via `demo.launch(head=...)` on page load
2. Store `Niivue` class in `window.Niivue`
3. gr.HTML contains canvas with `data-*` attributes for URLs
4. MutationObserver watches for gr.HTML value changes
5. When URLs change, reinitialize viewer

```python
NIIVUE_HEAD = """
<script type="module">
    import { Niivue } from 'https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js';
    window.Niivue = Niivue;
    window.nvInstances = {};

    // Watch for new niivue containers
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === 1) {
                    const containers = node.querySelectorAll('[data-niivue-dwi]');
                    containers.forEach(initContainer);
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    async function initContainer(container) {
        const dwiUrl = container.dataset.niivueDwi;
        const maskUrl = container.dataset.niivueMask;
        const canvas = container.querySelector('canvas');

        const nv = new Niivue({ logging: true });
        await nv.attachToCanvas(canvas);
        const volumes = [{ url: dwiUrl }];
        if (maskUrl) volumes.push({ url: maskUrl, colormap: 'red', opacity: 0.5 });
        await nv.loadVolumes(volumes);
    }
</script>
"""

def create_niivue_html(dwi_url, mask_url):
    return f"""
    <div data-niivue-dwi="{dwi_url}" data-niivue-mask="{mask_url or ''}">
        <canvas style="width:100%; height:500px;"></canvas>
    </div>
    """
```

### Option 2: gradio-iframe with PostMessage

**Complexity:** High
**Risk:** Low (most isolated)

**How it works:**
1. Create standalone `niivue-viewer.html`
2. Serve via Gradio's allowed_paths
3. Use postMessage to send volume URLs
4. iframe handles all WebGL

### Option 3: Abandon Gradio for Viewer

**Complexity:** Very High
**Risk:** High (major rewrite)

**How it works:**
1. Split app: Gradio for controls, FastAPI for viewer
2. Two endpoints, iframe embedding
3. Complete isolation

### Option 4: Wait for Gradio gr.Custom

**Complexity:** None (waiting)
**Risk:** Unknown timeline

[Issue #12074](https://github.com/gradio-app/gradio/issues/12074) proposes `gr.Custom` class for simpler custom components. This would solve many of our issues but has no timeline.

---

## PART 6: What NOT to Do

1. **DO NOT** put `<script>` tags in gr.HTML value - they won't execute
2. **DO NOT** use `gr.Blocks(head=...)` - that's Gradio 5 syntax
3. **DO NOT** rely on js_on_load for reactive updates - it only runs once
4. **DO NOT** assume CDN imports work without testing - CSP may block
5. **DO NOT** ignore the custom component in `packages/` - it may interfere

---

## PART 7: Testing Checklist Before Any Deploy

- [ ] Verify script execution: Add `console.log('HEAD SCRIPT LOADED')` to head=
- [ ] Test CDN access: Manually fetch `https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js`
- [ ] Check CSP headers: Inspect Network tab for blocked resources
- [ ] Test MutationObserver: Verify it fires when gr.HTML updates
- [ ] Verify NiiVue initialization: Check for WebGL context errors
- [ ] Test volume loading: Ensure /gradio_api/file= URLs are accessible

---

## PART 8: Decision Required

**Before any code changes, senior review needed on:**

1. **Which approach to take?** (Option 1, 2, 3, or wait for 4)
2. **Should we remove the custom component entirely?** (`packages/niivueviewer/`)
3. **Is the gr.HTML approach acceptable** even if it requires MutationObserver hacks?
4. **Should we consider ditching Gradio** for the viewer portion?

---

## Sources

### Official Gradio Documentation
- [Custom CSS and JS Guide](https://www.gradio.app/guides/custom-CSS-and-JS)
- [Custom HTML Components Guide](https://www.gradio.app/guides/custom_HTML_components)
- [Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)
- [gr.HTML Docs](https://www.gradio.app/docs/gradio/html)

### GitHub Issues
- [#7649: WebGL Canvas rejected](https://github.com/gradio-app/gradio/issues/7649)
- [#4511: 3D Medical Images rejected](https://github.com/gradio-app/gradio/issues/4511)
- [#7026: style.css 404](https://github.com/gradio-app/gradio/issues/7026)
- [#6087: JS import breaks](https://github.com/gradio-app/gradio/issues/6087)
- [#11649: head= 404 issue](https://github.com/gradio-app/gradio/issues/11649)
- [#12074: Revisiting custom components](https://github.com/gradio-app/gradio/issues/12074)

### HuggingFace Forum
- [gr.HTML scripts don't work](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)

### Reference Implementations
- [TobiasPitters/bids-neuroimaging](https://huggingface.co/spaces/TobiasPitters/bids-neuroimaging) (FastAPI, works)
- [gradio-iframe PyPI](https://pypi.org/project/gradio-iframe/)
- [ipyniivue](https://github.com/niivue/ipyniivue) (Jupyter, different approach)

---

## Conclusion

**The fundamental problem:** Gradio is designed for simple input/output components, not complex WebGL canvases with their own lifecycle and state management. Every approach we've tried fights against Gradio's architecture.

**The reference implementation works** because it doesn't use Gradio at all - it uses FastAPI with raw HTML.

**UPDATED (2025-12-11):** HF Spaces test confirms:
- **Custom Svelte component = ROOT CAUSE of UI freeze** (now removed, app works)
- **gr.HTML `<script>` = does not execute** (as documented above)
- **Only remaining task:** Implement working NiiVue loading via `launch(head=...)` + MutationObserver

**Recommended path forward:** Option 1 (Head Script + MutationObserver) since:
1. App now works on HF Spaces
2. We just need to load NiiVue via `launch(head=...)`
3. Use data attributes + MutationObserver to trigger viewer init when data changes

**Next steps:** Senior review required before implementing any solution.
