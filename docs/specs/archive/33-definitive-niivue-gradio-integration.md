# Spec #33: Definitive NiiVue + Gradio Integration Analysis

**Date:** 2025-12-10
**Status:** RESEARCH COMPLETE
**Issue:** #24 (HF Spaces UI Frozen)

---

## Executive Summary

After exhaustive web research (December 2025), the definitive answer is:

| Approach | Works on HF Spaces? | Complexity | Recommended? |
|----------|---------------------|------------|--------------|
| FastAPI + Raw HTML (reference impl) | YES | Low | For standalone apps |
| gr.HTML + head= + js_on_load | YES (theoretically) | Medium | **YES - TRY THIS** |
| gradio-iframe component | MAYBE | Low | Fallback option |
| Custom Svelte Component | BROKEN | High | **NO - ABANDON** |

**The fundamental blocker**: Our custom Svelte component approach has multiple failure modes that are difficult to debug and fix. The Gradio team explicitly recommends custom components for specialized viewers, but the implementation is fragile.

---

## Our Stack

```
Gradio: >=6.0.0,<7.0.0
Svelte: ^5.43.4
@gradio/preview: 0.15.1
@niivue/niivue: 0.65.0
```

---

## What Works (Proven)

### 1. FastAPI + Raw HTML (Reference: TobiasPitters/bids-neuroimaging)

**Location:** `_reference_repos/bids-neuroimaging/main.py`

```python
# Returns raw HTML with inline <script type="module">
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <canvas id="niivue-canvas"></canvas>
    <script type="module">
        const { Niivue } = await import('https://unpkg.com/@niivue/niivue@0.57.0/dist/index.js');
        const nv = new Niivue({ logging: true });
        await nv.attachTo('niivue-canvas');
        await nv.loadVolumes([{ url: dataUrl }]);
    </script>
    """
```

**Why it works:**
- No Gradio framework interference
- Direct ES module import from CDN
- No Svelte compilation
- No StatusTracker, no i18n, no event system
- Just pure HTML + JavaScript

### 2. gr.HTML with head= Parameter (Gradio Official)

**Source:** [Gradio Custom CSS and JS Guide](https://www.gradio.app/guides/custom-CSS-and-JS)

```python
head = """
<script type="module">
    import { Niivue } from 'https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js';
    window.Niivue = Niivue;  // Expose globally
</script>
"""

with gr.Blocks(head=head) as demo:
    viewer = gr.HTML("""<canvas id="niivue-canvas"></canvas>""")
```

**Why this should work:**
- `head=` injects scripts before Gradio hydrates
- No custom component complexity
- NiiVue available globally via `window.Niivue`

### 3. gr.HTML with js_on_load (Gradio Official)

**Source:** [Gradio Custom HTML Components Guide](https://www.gradio.app/guides/custom_HTML_components)

```python
gr.HTML(
    value='<canvas id="niivue-canvas" width="640" height="480"></canvas>',
    js_on_load="""
        const canvas = element.querySelector('canvas');
        const nv = new window.Niivue({ logging: true });
        await nv.attachToCanvas(canvas);
        // Store reference for later use
        element._niivue = nv;
    """
)
```

**Caveat from docs:** "Event listeners attached in js_on_load are only attached once when the component is first rendered"

---

## What's Broken (Our Approach)

### Custom Svelte Component (packages/niivueviewer/)

**Known failure modes from GitHub issues:**

| Issue | Problem | Impact |
|-------|---------|--------|
| [#7026](https://github.com/gradio-app/gradio/issues/7026) | style.css 404 | Component hangs on loading |
| [#6087](https://github.com/gradio-app/gradio/issues/6087) | CJS vs ESM import | Dev server stuck |
| [#9879](https://github.com/gradio-app/gradio/issues/9879) | Templates undefined | Component fails to render |
| [#12074](https://github.com/gradio-app/gradio/issues/12074) | Custom components too complex | Proposed gr.Custom class |

**Our specific issues:**
1. StatusTracker requires `gradio.i18n` prop (fixed in PR #31, but still broken)
2. Templates may not be properly served on HF Spaces
3. WebGL canvas initialization timing conflicts with Gradio hydration
4. Event system (SSE/queue) can get stuck

**Gradio team's stance:**
- [Issue #7649](https://github.com/gradio-app/gradio/issues/7649): WebGL Canvas component rejected as "too niche"
- [Issue #4511](https://github.com/gradio-app/gradio/issues/4511): 3D medical images rejected, told to use custom component
- Irony: They say "use custom components" but custom components are fragile

---

## What's Impossible

1. **Native Gradio WebGL component** - Explicitly rejected by maintainers
2. **Reliable custom components with complex JS libraries** - Too many failure modes
3. **Debugging HF Spaces JS errors** - No browser DevTools access

---

## The Correct Solution

### Option A: gr.HTML + head= + js_on_load (Recommended)

**Why:**
- No custom component
- Uses official Gradio APIs
- NiiVue loaded from CDN (no bundling issues)
- No Svelte, no templates, no StatusTracker

**Implementation:**

```python
import gradio as gr

NIIVUE_HEAD = """
<script type="module">
    const { Niivue } = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
    window.Niivue = Niivue;
    console.log('[NiiVue] Library loaded globally');
</script>
"""

NIIVUE_HTML = """
<div id="niivue-container" style="width:100%; height:500px; background:#000;">
    <canvas id="niivue-canvas" style="width:100%; height:100%;"></canvas>
</div>
"""

NIIVUE_JS_ON_LOAD = """
(async () => {
    try {
        const canvas = element.querySelector('#niivue-canvas');
        if (!canvas) {
            console.error('[NiiVue] Canvas not found');
            return;
        }
        const nv = new window.Niivue({
            backColor: [0, 0, 0, 1],
            show3Dcrosshair: true,
            logging: true
        });
        await nv.attachToCanvas(canvas);
        element._niivue = nv;
        console.log('[NiiVue] Viewer initialized');
    } catch (err) {
        console.error('[NiiVue] Init error:', err);
    }
})();
"""

with gr.Blocks(head=NIIVUE_HEAD) as demo:
    viewer = gr.HTML(value=NIIVUE_HTML, js_on_load=NIIVUE_JS_ON_LOAD)
```

### Option B: gradio-iframe (Fallback)

**Source:** [gradio-iframe PyPI](https://pypi.org/project/gradio-iframe/)

```python
from gradio_iframe import iFrame

# Serve standalone NiiVue HTML as static file
with gr.Blocks() as demo:
    viewer = iFrame(value="/static/niivue-viewer.html", height=500)
```

**Pros:** Complete isolation from Gradio
**Cons:** Height issues, separate HTML file to maintain

### Option C: Abandon Gradio (Nuclear)

Use FastAPI like the reference implementation. Lose all Gradio benefits (dropdowns, buttons, state management).

---

## Action Plan

1. **Delete custom component** (`packages/niivueviewer/`)
2. **Implement Option A** (gr.HTML + head= + js_on_load)
3. **Test locally**
4. **Deploy to HF Spaces**
5. **If fails, try Option B** (gradio-iframe)

---

## Sources

- [Gradio Custom CSS and JS](https://www.gradio.app/guides/custom-CSS-and-JS)
- [Gradio Custom HTML Components](https://www.gradio.app/guides/custom_HTML_components)
- [GitHub #7649: WebGL Canvas rejected](https://github.com/gradio-app/gradio/issues/7649)
- [GitHub #4511: 3D Medical Images rejected](https://github.com/gradio-app/gradio/issues/4511)
- [GitHub #7026: style.css 404](https://github.com/gradio-app/gradio/issues/7026)
- [GitHub #6087: JS import breaks](https://github.com/gradio-app/gradio/issues/6087)
- [GitHub #12074: Revisiting custom components](https://github.com/gradio-app/gradio/issues/12074)
- [gradio-iframe PyPI](https://pypi.org/project/gradio-iframe/)
- [NiiVue Docs](https://niivue.com/docs/)
- [Reference Implementation](https://huggingface.co/spaces/TobiasPitters/bids-neuroimaging)

---

## Conclusion

**The custom Svelte component approach is fundamentally flawed for WebGL viewers.**

The Gradio framework is designed for simple input/output components, not complex WebGL canvases with their own lifecycle. Every fix we've attempted has revealed another layer of issues.

**The solution is to use Gradio's official APIs (gr.HTML + head= + js_on_load) instead of fighting the framework with custom components.**
