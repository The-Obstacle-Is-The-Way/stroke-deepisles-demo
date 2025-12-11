# Spec #35: FINAL ATTEMPT - gradio-iframe

**Date:** 2025-12-10
**Status:** NOT STARTED
**Priority:** P0 - LAST ATTEMPT BEFORE ABANDONING GRADIO

---

## Executive Summary

**This is the LAST thing to try before abandoning Gradio for NiiVue integration.**

After 2+ days and 6+ failed approaches, `gradio-iframe` is the ONE documented approach we never actually implemented.

---

## What We Tried (ALL FAILED)

| # | Approach | Result | Why It Failed |
|---|----------|--------|---------------|
| 1 | gr.HTML + inline `<script>` | FAILED | innerHTML doesn't execute scripts (browser security) |
| 2 | js_on_load + `import()` | FAILED | Async import blocks Svelte hydration |
| 3 | head= + `import()` | FAILED | Same async import blocking issue |
| 4 | head_paths= | FAILED | Same issue |
| 5 | Vendored NiiVue + import() | FAILED | CSP fixed, but import() still blocks |
| 6 | Custom Svelte Component | FAILED | Froze entire UI (StatusTracker i18n, templates) |

---

## What We Have NOT Tried

| Approach | Why It Might Work |
|----------|-------------------|
| **gradio-iframe** | Scripts execute normally in iframes - bypasses ALL the innerHTML/hydration issues |

---

## The Implementation

### Step 1: Install gradio-iframe

```bash
pip install gradio-iframe
```

Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing deps ...
    "gradio-iframe>=0.0.10",
]
```

### Step 2: Create standalone NiiVue HTML file

Create `src/stroke_deepisles_demo/ui/assets/niivue-viewer.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #000; height: 100vh; display: flex; align-items: center; justify-content: center; }
        #canvas { width: 100%; height: 100%; }
        .error { color: #f66; text-align: center; padding: 20px; }
        .loading { color: #888; text-align: center; }
    </style>
</head>
<body>
    <canvas id="canvas"></canvas>
    <script type="module">
        import { Niivue } from 'https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js';

        const nv = new Niivue({
            backColor: [0, 0, 0, 1],
            show3Dcrosshair: true,
        });

        await nv.attachToCanvas(document.getElementById('canvas'));

        // Listen for volume URLs from parent Gradio app
        window.addEventListener('message', async (event) => {
            const { dwiUrl, maskUrl } = event.data;
            if (!dwiUrl) return;

            const volumes = [{ url: dwiUrl }];
            if (maskUrl) {
                volumes.push({ url: maskUrl, colormap: 'red', opacity: 0.5 });
            }

            await nv.loadVolumes(volumes);
            nv.setSliceType(nv.sliceTypeMultiplanar);
        });

        // Signal ready to parent
        window.parent.postMessage({ type: 'niivue-ready' }, '*');
    </script>
</body>
</html>
```

**NOTE:** If HF Spaces CSP blocks unpkg.com, use vendored local path instead.

### Step 3: Modify components.py

Replace gr.HTML with iFrame:

```python
from gradio_iframe import iFrame

def create_results_display() -> dict[str, Any]:
    with gr.Tabs():
        with gr.Tab("Interactive 3D"):
            niivue_viewer = iFrame(
                value="/gradio_api/file=/path/to/niivue-viewer.html",
                height=500,
                label="NiiVue Viewer",
            )
        # ... rest unchanged
```

### Step 4: Modify app.py to send postMessage

After segmentation completes, send volume URLs to iframe:

```python
# In run_segmentation return, include JS to postMessage
niivue_update_js = f"""
() => {{
    const iframe = document.querySelector('iframe');
    if (iframe) {{
        iframe.contentWindow.postMessage({{
            dwiUrl: '{dwi_url}',
            maskUrl: '{mask_url or ""}'
        }}, '*');
    }}
}}
"""
```

Wire this with `.then(fn=None, js=niivue_update_js)` on the click handler.

### Step 5: Add allowed_paths

```python
demo.launch(
    allowed_paths=[str(assets_dir)],  # So iframe HTML is served
)
```

---

## Why This Should Work

1. **Iframe is a separate document** - not affected by Gradio's innerHTML
2. **Scripts execute normally** - no innerHTML blocking
3. **No Svelte hydration interference** - iframe is isolated
4. **postMessage is standard** - reliable cross-frame communication
5. **Simple** - no build system, no npm, no Svelte components

---

## Known Risks

| Risk | Mitigation |
|------|------------|
| gradio-iframe abandoned (last update Jan 2024) | Iframe is simple; unlikely to break with Gradio updates |
| Height issues | Set explicit height=500 |
| CSP blocks CDN in iframe | Use vendored NiiVue if needed |
| postMessage timing | iframe signals ready before we send URLs |

---

## Success Criteria

- [ ] NiiVue viewer loads in iframe (no errors)
- [ ] Volume URLs sent via postMessage
- [ ] Volumes render in viewer
- [ ] Works on HuggingFace Spaces
- [ ] No UI freeze

---

## If This Fails

**Abandon Gradio for NiiVue integration.**

Options after failure:
1. Keep Gradio but remove NiiVue (2D matplotlib only)
2. Replace Gradio entirely with FastAPI + raw HTML
3. Use a different viewer library

---

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `gradio-iframe>=0.0.10` |
| `src/stroke_deepisles_demo/ui/assets/niivue-viewer.html` | NEW - standalone viewer |
| `src/stroke_deepisles_demo/ui/components.py` | Replace gr.HTML with iFrame |
| `src/stroke_deepisles_demo/ui/app.py` | Add postMessage JS, update allowed_paths |

---

## Estimated Effort

**2-3 hours** if it works.
**0 hours** if we abandon after this fails.

---

## Decision

This is the **FINAL** attempt. If gradio-iframe fails on HF Spaces, we abandon NiiVue integration with Gradio and either:
- Ship with 2D matplotlib only
- Rewrite without Gradio

No more hacks. No more "one more thing to try."
