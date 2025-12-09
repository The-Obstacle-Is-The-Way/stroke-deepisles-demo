# Bug #10: NiiVue 3D Viewer Renders Black Screen on HF Spaces

## Status: PARTIALLY FIXED → See Bug #11

**Date:** 2025-12-09
**Branch:** `fix/niivue-js-on-load` (merged), now `fix/niivue-js-rerun`
**Discovered:** After fixing Bug #9 (DeepISLES subprocess bridge)

### Fix Applied (2025-12-09) - PARTIAL

Implemented `js_on_load` approach (Solution 1 from this spec):

1. **`viewer.py`**: Removed `<script>` tags, added `NIIVUE_JS_ON_LOAD` constant
2. **`components.py`**: Added `js_on_load=NIIVUE_JS_ON_LOAD` to gr.HTML
3. **All 130 tests pass locally**

The HTML now uses `data-*` attributes to pass volume URLs, and JavaScript
executes via `js_on_load` instead of inline `<script>` tags.

### Continued in Bug #11

After HF Spaces deployment, we discovered that `js_on_load` **only runs once
on component mount**, not on value updates. This means the NiiVue viewer
initializes correctly on page load, but when `run_segmentation()` updates
the gr.HTML value with new data-* attributes, the JS doesn't re-execute.

**See [Bug #11](./11-bug-niivue-js-on-load-not-rerunning.md) for the complete
analysis and the verified fix using `.then(fn=None, js=...)`.**

---

## TL;DR - ROOT CAUSE

**Gradio's `gr.HTML` component does NOT execute `<script>` tags (including `type="module"`).**

Our code embeds NiiVue initialization JavaScript inside `<script type="module">` tags within the HTML value. Gradio intentionally ignores these for security reasons. The canvas renders but NiiVue never initializes → black screen.

---

## Symptom

After successful DeepISLES inference on HF Spaces, the NiiVue 3D viewer component (top-right panel) renders as a completely black rectangle. No brain scan or mask overlay is visible.

**What IS working:**
- DeepISLES inference completes successfully (~32 seconds)
- Slice Comparison (matplotlib 2D view) renders correctly
- Metrics JSON displays correctly
- Download button provides the prediction mask
- Ground truth overlay in Slice Comparison works

**What is NOT working:**
- NiiVue WebGL 3D viewer shows black screen
- No error message displayed in the viewer area
- No visible WebGL error fallback message

**What SHOULD appear:**
- Multi-planar view (axial/coronal/sagittal slices)
- Optional 3D volume rendering
- Interactive crosshairs for navigation
- DWI volume as grayscale background
- Prediction mask as semi-transparent red overlay

---

## Root Cause Analysis

### Evidence Chain

1. **[HuggingFace Forum](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)**:
   > "You can't load scripts via `gr.HTML`"

2. **[Gradio Official Docs](https://www.gradio.app/docs/gradio/html)**:
   > "Only static HTML is rendered (e.g., no JavaScript). To render JavaScript, use the `js` or `head` parameters"

3. **[Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)**:
   > The `js` and `head` parameters moved from `gr.Blocks()` to `launch()` in Gradio 6

4. **[GitHub Issue #10250](https://github.com/gradio-app/gradio/issues/10250)**:
   > Known issue with JavaScript in `head` param not executing reliably

### Our Code (BROKEN)

```python
# viewer.py:324-385 - Returns HTML with embedded script tags
def create_niivue_html(volume_url, mask_url, height=400) -> str:
    return f"""
    <div id="{container_id}" style="...">
        <canvas id="{canvas_id}" style="..."></canvas>
    </div>
    <script type="module">
        // THIS ENTIRE BLOCK IS IGNORED BY GRADIO!
        (async function() {{
            const niivueModule = await import('{NIIVUE_CDN_URL}');
            const Niivue = niivueModule.Niivue;
            const nv = new Niivue({{...}});
            await nv.attachToCanvas(document.getElementById('{canvas_id}'));
            await nv.loadVolumes([{{ url: {volume_url_js} }}]);
            // ... more initialization
        }})();
    </script>
    """

# components.py:42 - Basic HTML component without js_on_load
niivue_viewer = gr.HTML(label="Interactive 3D Viewer")  # No js_on_load!
```

### Why It Fails

1. `gr.HTML` receives our HTML string as `value`
2. Gradio renders the `<div>` and `<canvas>` elements (static HTML)
3. Gradio **strips or ignores** the `<script>` tags for security
4. NiiVue JavaScript never executes
5. Canvas remains empty → black screen
6. Our try/catch error handling never runs (script doesn't execute at all)

---

## Secondary Issues

### Issue 1: Base64 Payload Size (~65MB)

Even if JavaScript executed, we're passing massive base64-encoded NIfTI data:

| File | Raw Size | Base64 Size |
|------|----------|-------------|
| DWI | 30.1 MB | ~40 MB |
| ADC | 17.7 MB | ~24 MB |
| **Total** | ~48 MB | **~65 MB** |

This could cause:
- Browser memory issues
- Gradio payload limits
- Slow/failed rendering

### Issue 2: Gradio 6 Breaking Changes

Our code uses Gradio 5.x patterns. In Gradio 6.x:
- `js`, `head`, `head_paths` moved from `gr.Blocks()` to `launch()`
- `padding` default changed from `True` to `False`
- `js_on_load` is now the proper way for component-level JavaScript

### Issue 3: No Error Visibility

Our JavaScript has try/catch that should display errors in the container, but since the script never executes, the error handling never runs. The canvas just stays black with no feedback to the user.

---

## Code Locations

| File | Lines | Description |
|------|-------|-------------|
| `src/stroke_deepisles_demo/ui/viewer.py` | 277-385 | `create_niivue_html()` - generates broken HTML |
| `src/stroke_deepisles_demo/ui/viewer.py` | 34-51 | `nifti_to_data_url()` - base64 encoding |
| `src/stroke_deepisles_demo/ui/app.py` | 101-117 | NiiVue HTML generation in `run_segmentation()` |
| `src/stroke_deepisles_demo/ui/components.py` | 41-42 | `gr.HTML` component creation (missing js_on_load) |

---

## External Validation (2025-12-09)

An external agent review claimed `js_on_load` does not exist. **This claim was REFUTED.**

### Verification Results

| Claim | Status | Evidence |
|-------|--------|----------|
| "gr.HTML does NOT have js_on_load parameter" | ❌ **REFUTED** | [Gradio Docs](https://www.gradio.app/docs/gradio/html) show `js_on_load` with default value |
| "js_on_load was added in PR #12098" | ✅ Confirmed | Part of "gr.HTML custom components" feature |
| "Base64 payload (~65MB) is a risk" | ✅ Confirmed | Valid concern, should use file URLs |
| "CSP headers may block CDN" | ⚠️ Possible | HF Spaces typically allows unpkg.com, but worth testing |

### Validated `js_on_load` Signature

```python
js_on_load: str | None = "element.addEventListener('click', function() { trigger('click') });"
```

**Available in js_on_load context:**
- `element` - The HTML DOM element
- `trigger(event_name)` - Fire Gradio events
- `props` - Access component props including `props.value`

**Untested (needs verification):**
- Async/await patterns
- Dynamic `import()` for CDN modules
- Error propagation to Gradio

---

## Proposed Solutions (Ranked)

### Solution 1: Use `js_on_load` Parameter (Recommended)

Gradio 6's `gr.HTML` supports `js_on_load` for component-level JavaScript (added in PR #12098):

```python
def create_niivue_component(volume_url, mask_url, height=400):
    container_id = f"nv-{uuid.uuid4().hex[:8]}"

    html_content = f'<div id="{container_id}" style="height:{height}px;background:#000;"><canvas></canvas></div>'

    js_code = f"""
        (async () => {{
            try {{
                const {{ Niivue }} = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
                const nv = new Niivue({{ logging: false, backColor: [0,0,0,1] }});
                await nv.attachToCanvas(element.querySelector('canvas'));
                await nv.loadVolumes([{{ url: {json.dumps(volume_url)} }}]);
                nv.setSliceType(nv.sliceTypeMultiplanar);
            }} catch (e) {{
                element.innerHTML = '<div style="color:#fff;padding:20px;">Error: ' + e.message + '</div>';
            }}
        }})();
    """

    return gr.HTML(
        value=html_content,
        js_on_load=js_code,
        label="Interactive 3D Viewer"
    )
```

**Pros:** Native Gradio 6 approach, component-scoped
**Cons:** May have issues with dynamic import in js_on_load context

### Solution 2: Use `head` Parameter in `launch()`

Load NiiVue globally via the `head` parameter:

```python
# app.py
NIIVUE_HEAD = '''
<script type="module">
    import { Niivue } from 'https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js';
    window.Niivue = Niivue;
</script>
'''

demo.launch(
    head=NIIVUE_HEAD,
    server_name="0.0.0.0",
    server_port=7860
)
```

**Pros:** Loads library once, available globally
**Cons:** GitHub Issue #10250 reports unreliable execution

### Solution 3: Server-Side File Serving

Instead of base64 data URLs, serve NIfTI files via Gradio's file system:

```python
# Use Gradio's file URL instead of data URLs
from gradio import FileData
file_data = FileData(path=str(dwi_path))
# Pass file_data.url to NiiVue instead of base64
```

**Pros:** Avoids 65MB payload, better memory efficiency
**Cons:** Requires refactoring data flow, CORS considerations

### Solution 4: Custom Gradio Component

Build a proper `gradio_niivue` package:

```bash
gradio cc create NiiVue --template HTML
# Implement Svelte frontend with NiiVue
# Publish to PyPI
```

**Pros:** Most robust, reusable, proper architecture
**Cons:** Significant development effort

### Solution 5: Enhanced 2D Fallback (Simplest)

Remove NiiVue entirely, enhance matplotlib visualization:

```python
def create_results_display():
    with gr.Group():
        # Remove: niivue_viewer = gr.HTML(...)

        # Enhanced 2D visualization
        slice_plot = gr.Plot(label="Multi-View Comparison")
        slice_slider = gr.Slider(label="Slice", minimum=0, maximum=100)

        # Add orthogonal views
        with gr.Row():
            axial_plot = gr.Plot(label="Axial")
            coronal_plot = gr.Plot(label="Coronal")
            sagittal_plot = gr.Plot(label="Sagittal")
```

**Pros:** Eliminates WebGL complexity, works reliably
**Cons:** Loses 3D interactivity, less impressive demo

---

## Investigation Steps

### Step 0: Test Async/Await in js_on_load (CRITICAL)
Before implementing Solution 1, verify async works:
```python
import gradio as gr

with gr.Blocks() as demo:
    html = gr.HTML(
        value="<div>Testing async...</div>",
        js_on_load="""
            (async () => {
                element.innerText = 'Async started...';
                await new Promise(r => setTimeout(r, 1000));
                element.innerText = 'Async works!';
                element.style.background = 'green';
            })();
        """
    )

demo.launch()
```

If this shows "Async works!" with green background after 1 second, async is supported.

### Step 1: Verify js_on_load Works (Basic)
Create minimal test:
```python
import gradio as gr

with gr.Blocks() as demo:
    html = gr.HTML(
        value="<div id='test'>Loading...</div>",
        js_on_load="element.style.background='green'; element.innerText='JS Works!';"
    )

demo.launch()
```

### Step 2: Test Dynamic Import in js_on_load
```python
js_on_load="""
    (async () => {
        const mod = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
        console.log('NiiVue loaded:', mod);
        element.innerText = 'Import succeeded!';
    })();
"""
```

### Step 3: Check Browser Console
1. Open HF Spaces demo
2. Open DevTools (F12) → Console
3. Look for errors related to:
   - Module loading failures
   - WebGL context issues
   - CORS errors
   - Memory errors

### Step 4: Test with Smaller Files
Create downsampled test NIfTI (~1MB) to isolate size vs JS issues.

---

## Related Issues

- **Bug #9**: DeepISLES modules not found (FIXED - subprocess bridge)
- **Bug #8**: HF Spaces streaming hang (FIXED)
- **Technical Debt**: NiiVue memory overhead (P2)
- **[Gradio #4511](https://github.com/gradio-app/gradio/issues/4511)**: 3D medical image support request (closed, not planned)
- **[Gradio #10250](https://github.com/gradio-app/gradio/issues/10250)**: JS in head param issues (open)

---

## Priority Assessment

**Severity:** P2 (Medium)
- Core inference pipeline works correctly
- 2D visualization provides adequate fallback
- No data loss or security impact
- Demo is functional for evaluation purposes

**Impact:**
- Less impressive without 3D viewer
- Users can still evaluate predictions via 2D slices
- Download functionality unaffected

**Recommendation:**
1. First, validate inference accuracy across multiple cases
2. Then attempt Solution 1 (js_on_load) as quick fix
3. If that fails, implement Solution 5 (enhanced 2D) for reliability
4. Consider Solution 4 (custom component) for future enhancement

---

## References

- [Gradio HTML Docs](https://www.gradio.app/docs/gradio/html)
- [Gradio Custom HTML Components Guide](https://www.gradio.app/guides/custom_HTML_components)
- [Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)
- [HuggingFace Forum: JS doesn't work in gr.HTML](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)
- [GitHub Issue #10250: JS in head param](https://github.com/gradio-app/gradio/issues/10250)
- [GitHub Issue #4511: 3D Medical Images](https://github.com/gradio-app/gradio/issues/4511)
- [NiiVue GitHub](https://github.com/niivue/niivue)
- [ipyniivue (Jupyter Widget)](https://github.com/niivue/ipyniivue)
- [Gradio 6 Announcement](https://alternativeto.net/news/2025/11/gradio-6-released-with-faster-performance-for-creating-machine-learning-apps-in-python/)

---

## Appendix: HF Spaces Logs

```text
INFO: Running segmentation for sub-stroke0002
INFO: Case sub-stroke0002 ready: DWI=20.9MB, ADC=12.6MB
INFO: DeepISLES subprocess completed in 30.88s
```

Note: No JavaScript errors visible in server logs (client-side only).
