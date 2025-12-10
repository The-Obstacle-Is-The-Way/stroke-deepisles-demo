# Bug #11: NiiVue js_on_load Doesn't Re-run on Value Update

## Status: FIXED

**Date:** 2025-12-09
**Branch:** `fix/niivue-js-rerun`
**Fixed By:** Implementing `.then(fn=None, js=NIIVUE_UPDATE_JS)` pattern with correct `document.querySelector` context.
**Related:** Bug #10 (Fixed)

---

## TL;DR - ROOT CAUSE

**Gradio's `js_on_load` only runs ONCE when the component first mounts.**

When we update the `gr.HTML` value with new content (after segmentation), the `js_on_load` code does NOT re-execute. The HTML updates, but the JavaScript initialization never runs.

---

## Symptom

After successful DeepISLES inference on HF Spaces:
- Viewer shows "Loading viewer..." (initial HTML state)
- Status never changes to "Checking WebGL2..." or "Loading NiiVue..."
- No error message displayed
- No brain scan visible

**What IS working:**
- DeepISLES inference completes (~36 seconds)
- Slice Comparison (matplotlib 2D view) renders correctly
- Metrics JSON displays correctly
- Download button provides the prediction mask
- Initial HTML renders with data-* attributes

**What is NOT working:**
- js_on_load JavaScript doesn't re-run when value updates
- NiiVue never initializes after segmentation

---

## Evidence

### Gradio Documentation

From [Custom HTML Components Guide](https://www.gradio.app/guides/custom_HTML_components):

> "Event listeners attached in `js_on_load` are only attached **once** when the component is first rendered. If your component creates new elements dynamically that need event listeners, attach the event listener to a parent element..."

### Observed Behavior

1. Page loads → js_on_load runs → No volumeUrl → Shows "Waiting for segmentation..."
2. User clicks "Run Segmentation"
3. DeepISLES runs successfully
4. `run_segmentation()` returns new HTML with data-volume-url attribute
5. gr.HTML value updates with new HTML
6. **js_on_load does NOT re-run** ← THE BUG
7. Viewer shows "Loading viewer..." (static HTML, no JS executed)

### Server Logs (Working)

```text
INFO: Running segmentation for sub-stroke0001
INFO: DeepISLES subprocess completed in 35.73s
```

Inference works. The problem is client-side JavaScript execution.

---

## Code Flow Analysis

### Current Implementation (BROKEN)

```python
# components.py - js_on_load set once at component creation
niivue_viewer = gr.HTML(
    label="Interactive 3D Viewer",
    js_on_load=NIIVUE_ON_LOAD_JS,  # Runs ONCE on mount
)

# app.py - returns new HTML value after segmentation
def run_segmentation(...):
    # ... inference ...
    niivue_html = create_niivue_html(dwi_url, mask_url)
    return niivue_html, ...  # Value updates, but js_on_load doesn't re-run
```

### Why It Fails

1. Component mounts → js_on_load runs (no data yet)
2. Value updates → HTML re-renders, js_on_load SKIPPED
3. New HTML has data-* attributes but no JS execution

---

## Proposed Solutions (Ranked)

### Solution 1: Use `js` Parameter on Event Handler (Recommended)

Gradio allows running JavaScript after an event completes:

```python
run_btn.click(
    fn=run_segmentation,
    inputs=[...],
    outputs=[results["niivue_viewer"], ...],
).then(
    fn=None,  # MUST be explicit!
    js=NIIVUE_UPDATE_JS,  # ⚠️ CANNOT reuse NIIVUE_ON_LOAD_JS - different context!
)
```

**Pros:** Native Gradio pattern, runs after each update
**Cons:** Requires separate JS constant (see "Different JS Context" section below)

**⚠️ CRITICAL:** The `js` param does NOT have access to `element`. You must use
`document.querySelector()` instead. See the corrected JavaScript in the
"Recommended Implementation" section.

### Solution 2: MutationObserver in js_on_load

Watch for DOM changes and re-initialize. This approach IS valid because
`js_on_load` has access to `element`:

```javascript
// In js_on_load - 'element' IS available here
const initNiiVue = async () => {
    const container = element.querySelector('.niivue-viewer') || element;
    const volumeUrl = container.dataset.volumeUrl;
    if (!volumeUrl) return;
    // ... NiiVue initialization code ...
};

// Watch for attribute changes (when Python updates data-volume-url)
const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
        if (mutation.type === 'attributes' &&
            mutation.attributeName.startsWith('data-')) {
            initNiiVue();
            break;
        }
    }
});

// Observe the element for attribute changes
observer.observe(element, {
    attributes: true,
    subtree: true,
    attributeFilter: ['data-volume-url', 'data-mask-url']
});

// Initial check
initNiiVue();
```

**Pros:** Self-contained in js_on_load, no separate event wiring needed
**Cons:** More complex, relies on Gradio updating DOM attributes (may not work
if Gradio replaces the entire element instead of updating attributes)

### Solution 3: Use gradio-iframe Component

The `gradio-iframe` package allows JavaScript to execute normally:

```python
from gradio_iframe import iFrame

niivue_viewer = iFrame(
    value=create_niivue_html_with_script(...),  # Scripts execute in iframe
)
```

**Pros:** Scripts execute normally inside iframe
**Cons:** Additional dependency, iframe quirks

### Solution 4: Embed JS in HTML via data: URL iframe

Self-contained iframe with script:

```python
def create_niivue_html(...):
    html_with_script = f'''<script>...</script><canvas>...</canvas>'''
    encoded = base64.b64encode(html_with_script.encode()).decode()
    return f'<iframe src="data:text/html;base64,{encoded}"></iframe>'
```

**Pros:** No external dependency, scripts execute
**Cons:** Complex, potential CSP issues

### Solution 5: Custom Gradio Component

Build a proper `gradio_niivue` Svelte component:

```bash
gradio cc create NiiVue --template HTML
```

**Pros:** Most robust, proper lifecycle hooks
**Cons:** Significant development effort

---

## Investigation Steps

### Step 1: Test Solution 1 (js param on .then())

```python
run_btn.click(
    fn=run_segmentation,
    inputs=[...],
    outputs=[...],
).then(
    fn=None,
    js="console.log('then JS ran'); console.log(document.querySelector('.niivue-viewer'));"
)
```

Verify:
- Does `js` run after value update?
- Does it have access to the updated DOM?

### Step 2: Test Solution 2 (MutationObserver)

Add observer to js_on_load and check if it triggers on value change.

### Step 3: Check Browser Console

Open DevTools and look for:
- JavaScript errors
- Console logs from js_on_load
- Network requests to NiiVue CDN

---

## Temporary Workaround

The 2D Slice Comparison view works correctly and provides adequate visualization for evaluation purposes while we fix the 3D viewer.

---

## Priority Assessment

**Severity:** P1 (High)
- 3D viewer is a key feature for the demo
- The fix we deployed doesn't fully work
- Blocks demo usability for 3D visualization

**Impact:**
- Users see "Loading viewer..." indefinitely
- 2D fallback still works
- Demo is partially functional

---

## Deep Web Research (2025-12-09)

### Relationship Between Bug #10 and Bug #11

**They are the SAME underlying issue with two symptoms:**

1. **Bug #10**: Gradio strips `<script>` tags from gr.HTML for XSS security
2. **Bug #11**: Gradio's `js_on_load` only runs once on component mount

Both stem from Gradio's design decision to limit JavaScript execution in HTML components for security reasons.

### Verified Gradio Behavior (from official docs)

#### js_on_load Limitation (CONFIRMED)

From [Gradio Custom HTML Components](https://www.gradio.app/guides/custom_HTML_components):

> "Event listeners attached in `js_on_load` are **only attached once** when the component is first rendered."

#### Solution 1 VALIDATED: `.then(fn=None, js=...)`

From [Gradio Custom CSS and JS](https://www.gradio.app/guides/custom-CSS-and-JS):

> "You can pass both a JavaScript function and a Python function (in which case the JavaScript function is run first) or **only Javascript (and set the Python `fn` to `None`)**."

**Critical Implementation Detail** from [GitHub Issue #6729](https://github.com/gradio-app/gradio/issues/6729):

> "`js` without `fn` is executed only if `fn` is **explicitly** set to `None`"

```python
# WORKS
b1.click(js=js, fn=None)

# DOES NOT WORK
b2.click(js=js)  # fn defaults to something, not None
```

#### js Parameter Signature

From [Gradio HTML Docs](https://www.gradio.app/docs/gradio/html):

> "The `js` parameter is an optional frontend js method to run before running 'fn'. Input arguments for js method are values of 'inputs' and 'outputs', return should be a list of values for output components."

### Alternative Solutions Research

#### gradio-iframe Package

From [PyPI gradio-iframe](https://pypi.org/project/gradio-iframe/):

- Version: 0.0.10 (Jan 2024)
- **JavaScript executes normally inside iframe**
- Known issues: Height doesn't always adjust, not fully responsive
- Status: Alpha, possibly abandoned (no updates in 12 months)
- **Risk:** May not be compatible with Gradio 6.x

#### MutationObserver Pattern

From [MDN MutationObserver](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver):

MutationObserver can watch for DOM changes and trigger re-initialization:

```javascript
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' &&
            mutation.attributeName === 'data-volume-url') {
            initNiiVue();
        }
    });
});
observer.observe(element, { attributes: true, attributeFilter: ['data-volume-url'] });
```

**Caveat from Gradio docs:**

> "Warning: The use of query selectors in custom JS and CSS is not guaranteed to work across Gradio versions that bind to Gradio's own HTML elements as the Gradio HTML DOM may change."

#### ipyniivue (Jupyter Widget)

From [GitHub ipyniivue](https://github.com/niivue/ipyniivue):

- Built on anywidget framework
- Designed for Jupyter, not Gradio
- No direct Gradio integration exists

### Recommended Implementation

Based on research, **Solution 1 (`.then(fn=None, js=...)`) is the correct fix**.

#### Step 1: Create a NEW JavaScript constant for event handlers

We **CANNOT** reuse `NIIVUE_ON_LOAD_JS` because it uses `element` which is not
available in the event handler context. We need a new constant:

```python
# viewer.py - NEW constant for event handler context
NIIVUE_UPDATE_JS = f"""
(async () => {{
    // ⚠️ NO 'element' available - must use document.querySelector()
    const container = document.querySelector('.niivue-viewer');
    if (!container) {{
        console.error('NiiVue container not found');
        return;
    }}

    const canvas = container.querySelector('canvas');
    const status = container.querySelector('.niivue-status');

    // Get URLs from data attributes
    const volumeUrl = container.dataset.volumeUrl;
    const maskUrl = container.dataset.maskUrl;

    // Skip if no volume URL
    if (!volumeUrl) {{
        console.log('No volume URL yet');
        return;
    }}

    try {{
        if (status) status.innerText = 'Loading NiiVue...';

        const {{ Niivue }} = await import('{NIIVUE_CDN_URL}');
        const nv = new Niivue({{
            logging: false,
            show3Dcrosshair: true,
            backColor: [0, 0, 0, 1]
        }});

        await nv.attachToCanvas(canvas);
        if (status) status.style.display = 'none';

        const volumes = [{{ url: volumeUrl, name: 'input.nii.gz' }}];
        if (maskUrl) {{
            volumes.push({{ url: maskUrl, colorMap: 'red', opacity: 0.5 }});
        }}

        await nv.loadVolumes(volumes);
        nv.setSliceType(nv.sliceTypeMultiplanar);
        nv.drawScene();

        console.log('NiiVue initialized via .then()');
    }} catch (error) {{
        console.error('NiiVue init error:', error);
        if (container) {{
            const errorDiv = document.createElement('div');
            errorDiv.style.cssText = 'color:#f66;padding:20px;text-align:center;';
            errorDiv.textContent = 'Error: ' + error.message;
            container.innerHTML = '';
            container.appendChild(errorDiv);
        }}
    }}
}})();
"""
```

#### Step 2: Wire up the event handler in app.py

```python
# app.py
from stroke_deepisles_demo.ui.viewer import NIIVUE_UPDATE_JS

run_btn.click(
    fn=run_segmentation,
    inputs=[case_selector, settings["fast_mode"], settings["show_ground_truth"]],
    outputs=[results["niivue_viewer"], results["slice_plot"], results["metrics"],
             results["download"], status],
).then(
    fn=None,  # MUST be explicit per GitHub Issue #6729!
    js=NIIVUE_UPDATE_JS,
)
```

**Why this works:**
1. Python `run_segmentation()` updates gr.HTML value with new data-* attributes
2. `.then()` chains after the click handler completes
3. `fn=None` tells Gradio to skip Python, run JS only
4. `js=NIIVUE_UPDATE_JS` runs our initialization code
5. JS uses `document.querySelector()` to find the updated DOM

### ⚠️ CRITICAL: Different JS Context (VERIFIED)

The `js` parameter on event handlers has a **completely different context** than `js_on_load`:

| Context | `js_on_load` | `js` on event handler |
|---------|--------------|----------------------|
| `element` | ✅ Available | ❌ **NOT available** |
| `props` | ✅ Available | ❌ **NOT available** |
| `trigger()` | ✅ Available | ❌ **NOT available** |
| Arguments | None | Receives input/output **values** |

From [Gradio Custom CSS and JS](https://www.gradio.app/guides/custom-CSS-and-JS):

> "Input arguments for js method are **values of 'inputs' and 'outputs'**"

Example from Gradio docs:
```python
reverse_btn.click(
    None, [subject, verb, object], output2,
    js="(s, v, o) => o + ' ' + v + ' ' + s"  # Receives VALUES, not DOM elements
)
```

**This is why we need TWO separate JavaScript constants:**
- `NIIVUE_ON_LOAD_JS` - Uses `element.querySelector()` (for initial mount)
- `NIIVUE_UPDATE_JS` - Uses `document.querySelector()` (for .then() handler)

### Risk Assessment: Is This Fixable?

| Approach | Feasibility | Risk Level | Notes |
|----------|-------------|------------|-------|
| `.then(fn=None, js=...)` | ✅ High | Low | Native Gradio, documented |
| MutationObserver | ✅ High | Medium | Complex, DOM stability warning |
| gradio-iframe | ⚠️ Medium | High | Abandoned, Gradio 6 compat unknown |
| data: URL iframe | ⚠️ Medium | Medium | CSP issues possible |
| Custom component | ✅ High | Low | Most work, most robust |

**Verdict: YES, this is fixable.** Solution 1 should work based on verified documentation.

---

## References

- [Gradio Custom HTML Components](https://www.gradio.app/guides/custom_HTML_components) - js_on_load limitation
- [Gradio Custom CSS and JS](https://www.gradio.app/guides/custom-CSS-and-JS) - js parameter docs
- [Gradio Event Listeners](https://www.gradio.app/docs/gradio/blocks#events) - .then() method
- [GitHub Issue #6729](https://github.com/gradio-app/gradio/issues/6729) - fn=None requirement
- [gradio-iframe PyPI](https://pypi.org/project/gradio-iframe/) - Alternative approach
- [ipyniivue GitHub](https://github.com/niivue/ipyniivue) - Jupyter widget (not Gradio)
- [MDN MutationObserver](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver) - DOM watching
- [Bug #10 Spec](./10-bug-niivue-viewer-black-screen.md) - Previous fix attempt
- [Issue #19](https://github.com/The-Obstacle-Is-The-Way/stroke-deepisles-demo/issues/19) - Base64 optimization (related)
