# Bug #10: NiiVue 3D Viewer Renders Black Screen on HF Spaces

## Status: OPEN (P2)

**Date:** 2025-12-09
**Branch:** `debug/niivue-viewer-black-screen`
**Discovered:** After fixing Bug #9 (DeepISLES subprocess bridge)

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

---

## Technical Analysis

### Component Architecture

The NiiVue viewer is implemented in `src/stroke_deepisles_demo/ui/viewer.py`:

```python
# viewer.py:277-385
def create_niivue_html(volume_url, mask_url, height=400) -> str:
    # Returns HTML with embedded JavaScript that:
    # 1. Creates a canvas element
    # 2. Dynamically imports NiiVue from CDN
    # 3. Loads base64-encoded NIfTI files
    # 4. Renders via WebGL2
```

**Key configurations:**
- NiiVue version: `0.65.0`
- CDN URL: `https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js`
- Container: `gr.HTML` Gradio component
- Data format: Base64 data URLs for NIfTI files

### Hypothesis 1: Data URL Size (LIKELY)

**Evidence:**
- DWI file: 30.1MB → ~40MB as base64
- ADC file: 17.7MB → ~24MB as base64
- Total data passed to HTML component: ~65MB+ per inference

**Problem:**
- Gradio's `gr.HTML` component may have payload size limits
- Base64 encoding adds 33% overhead
- Large strings may cause JavaScript memory issues
- Dynamic module import may fail silently with large data URLs

**Test:** Check browser console for memory/payload errors

### Hypothesis 2: CDN Accessibility (POSSIBLE)

**Evidence:**
- NiiVue loaded from `unpkg.com` CDN
- HF Spaces may have network restrictions or high latency
- Dynamic `import()` may timeout silently

**Problem:**
- CDN may be blocked or slow on HF Spaces infrastructure
- No timeout handling in the JavaScript code
- Error caught but container innerHTML update may not render

**Test:** Check browser Network tab for CDN requests

### Hypothesis 3: WebGL2 Context Limitations (POSSIBLE)

**Evidence:**
- HF Spaces runs in sandboxed iframe
- WebGL2 contexts may be restricted or limited
- Canvas size (500px height) should be reasonable

**Problem:**
- WebGL2 may be available but context creation fails
- Multiple WebGL contexts may exhaust GPU memory
- HF Spaces may have security restrictions on WebGL

**Test:** Check browser console for WebGL errors

### Hypothesis 4: Gradio HTML Component Script Execution (POSSIBLE)

**Evidence:**
- Using `<script type="module">` with dynamic import
- Gradio may sanitize or restrict script execution in HTML components
- IIFE pattern may not execute in Gradio's rendering context

**Problem:**
- Gradio 6.x may have changed HTML component behavior
- Script may not execute after DOM update
- Module scripts may be blocked by CSP

**Test:** Add console.log at script start to verify execution

---

## Code Locations

| File | Lines | Description |
|------|-------|-------------|
| `src/stroke_deepisles_demo/ui/viewer.py` | 277-385 | `create_niivue_html()` function |
| `src/stroke_deepisles_demo/ui/viewer.py` | 34-51 | `nifti_to_data_url()` base64 encoding |
| `src/stroke_deepisles_demo/ui/app.py` | 101-117 | NiiVue HTML generation in `run_segmentation()` |
| `src/stroke_deepisles_demo/ui/components.py` | 41-42 | `gr.HTML` component creation |

---

## Proposed Solutions

### Solution A: Server-Side File Serving (Recommended)

Instead of base64 data URLs, serve NIfTI files via Gradio's file serving:

```python
# Use Gradio's file URL system instead of data URLs
file_url = gr.File(value=dwi_path, visible=False).value
niivue_html = create_niivue_html(file_url, mask_url)
```

**Pros:**
- Avoids massive base64 payloads
- Better memory efficiency
- Streaming support

**Cons:**
- Requires refactoring data flow
- May have CORS issues

### Solution B: Fallback to Static Images

If WebGL fails, render server-side images:

```python
def create_niivue_html_with_fallback(volume_url, mask_url, fallback_img):
    # Try NiiVue, fallback to static image
    return f"""
    <div id="viewer">
        <img src="{fallback_img}" id="fallback" style="display:none;">
        <canvas id="niivue"></canvas>
    </div>
    <script>
        // On error, show fallback image
    </script>
    """
```

**Pros:**
- Graceful degradation
- Always shows something

**Cons:**
- Loses interactivity
- Two rendering paths to maintain

### Solution C: Chunk/Stream Data Loading

Load NIfTI files in chunks rather than single base64 blob:

```javascript
// Load file via fetch with streaming
const response = await fetch(niftiUrl);
const reader = response.body.getReader();
// Stream chunks to NiiVue
```

**Pros:**
- Better memory management
- Progress indication possible

**Cons:**
- Complex implementation
- NiiVue may not support streaming input

### Solution D: Remove NiiVue (Simplest)

Remove the 3D viewer entirely, rely on matplotlib 2D slices:

```python
# components.py - remove niivue_viewer
def create_results_display():
    with gr.Group():
        # Remove: niivue_viewer = gr.HTML(...)
        slice_plot = gr.Plot(label="Slice Comparison")
        # Add more 2D views if needed
```

**Pros:**
- Eliminates complexity
- Matplotlib works reliably
- Faster page load

**Cons:**
- Loses 3D interactivity
- Less impressive demo

---

## Investigation Steps

### Step 1: Browser Console Analysis
1. Open HF Spaces demo in browser
2. Open Developer Tools (F12)
3. Run inference
4. Check Console tab for errors
5. Check Network tab for CDN requests

### Step 2: Add Debug Logging
```javascript
// In create_niivue_html()
console.log('NiiVue script starting...');
console.log('Volume URL length:', volume_url.length);
// Add more checkpoints
```

### Step 3: Test with Smaller Files
- Create test case with downsampled NIfTI
- Check if smaller files render

### Step 4: Test NiiVue Standalone
- Create minimal HTML page with NiiVue
- Host on HF Spaces to test WebGL

---

## Related Issues

- Bug #9: DeepISLES modules not found (FIXED)
- Bug #8: HF Spaces streaming hang (FIXED)
- Technical Debt: NiiVue memory overhead (P2)

---

## Priority Assessment

**Severity:** P2 (Medium)
- Core inference works correctly
- 2D visualization works as fallback
- No data loss or security impact

**Impact:**
- Demo less impressive without 3D viewer
- Users can still evaluate predictions via 2D slices
- Download functionality unaffected

**Recommendation:** Fix after validating inference accuracy across more cases. Consider Solution D (remove NiiVue) if fix is complex, since 2D slices already provide adequate visualization.

---

## Appendix: HF Spaces Logs (Relevant Excerpt)

```
INFO: Running segmentation for sub-stroke0002
INFO: Case sub-stroke0002 ready: DWI=20.9MB, ADC=12.6MB
INFO: DeepISLES subprocess completed in 30.88s
```

Note: No JavaScript errors visible in server logs (client-side only).
