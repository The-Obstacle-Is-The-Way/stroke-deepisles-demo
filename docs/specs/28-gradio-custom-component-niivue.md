# Spec #28: Gradio Custom Component for NiiVue

**Date:** 2025-12-10
**Status:** REQUIRED - All gr.HTML hacks have failed (confirmed Dec 10)
**Blocks:** Issue #24 (HF Spaces "Loading..." forever)
**Effort:** Medium (2-3 days)
**Success Probability:** 90%

---

## Executive Summary

**All `gr.HTML` + JavaScript approaches have FAILED. This is the only path forward.**

Gradio maintainers have explicitly closed both:
- [Issue #4511](https://github.com/gradio-app/gradio/issues/4511) - NIfTI/medical imaging support → "Not planned"
- [Issue #7649](https://github.com/gradio-app/gradio/issues/7649) - WebGL canvas component → "Not planned"

Their official answer: **"Create a Gradio Custom Component."**

This spec documents what we need to build to properly integrate NiiVue (WebGL2 medical imaging viewer) into our Gradio app.

---

## Why Current Approach Fails

### What We've Tried

| Attempt | Why It Failed |
|---------|---------------|
| CDN import in js_on_load | HF Spaces CSP blocks external imports |
| Vendored NiiVue + dynamic import() | import() in js_on_load blocks Svelte hydration |
| head= parameter | Still uses ES module import, same problem |
| head_paths= parameter | Same as above |
| gr.set_static_paths() | File serving works, but JS loading mechanism broken |

### Root Cause

**We're fighting Gradio's architecture.** Gradio is built with Svelte and has specific lifecycle expectations:

1. `gr.HTML` strips `<script>` tags (security)
2. `js_on_load` runs during component mount - async operations can block hydration
3. ES module `import()` in any lifecycle hook can hang the entire app

**Gradio was not designed for custom WebGL content in `gr.HTML`.**

---

## The Solution: Gradio Custom Component

### What Is a Gradio Custom Component?

A Custom Component is a proper Svelte + Python component that integrates with Gradio's architecture:

```
gradio-niivue-viewer/
├── frontend/
│   ├── Index.svelte      # Svelte component (renders NiiVue)
│   ├── package.json      # Frontend deps (including niivue)
│   └── ...
├── backend/
│   └── gradio_niivue_viewer/
│       └── __init__.py   # Python component class
├── pyproject.toml        # Package definition
└── demo/
    └── app.py            # Example usage
```

### Why This Works

1. **Svelte-native**: Component integrates with Gradio's lifecycle properly
2. **Official pattern**: Gradio maintainers recommend this for WebGL
3. **Isolated loading**: NiiVue loads within the component, not globally
4. **Proper error handling**: Failures don't block app initialization
5. **Reusable**: Can publish to PyPI for others to use

---

## Technical Approach

### Phase 1: Scaffold Component (1 hour)

Use Gradio's CLI to create the component:

```bash
gradio cc create NiiVueViewer \
  --template Image \
  --overwrite
```

This creates the basic structure with Svelte frontend and Python backend.

### Phase 2: Implement Svelte Frontend (4-6 hours)

Modify `frontend/Index.svelte`:

```svelte
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Niivue } from '@niivue/niivue';
  import type { FileData } from '@gradio/client';

  export let value: {
    background_url: string | null;
    overlay_url: string | null;
  } | null = null;

  let container: HTMLDivElement;
  let nv: Niivue | null = null;

  onMount(async () => {
    nv = new Niivue({
      backColor: [0, 0, 0, 1],
      show3Dcrosshair: true,
    });
    await nv.attachToCanvas(container.querySelector('canvas'));
    await loadVolumes();
  });

  onDestroy(() => {
    if (nv) nv.dispose();
  });

  async function loadVolumes() {
    if (!nv || !value) return;
    const volumes = [];
    if (value.background_url) {
      volumes.push({ url: value.background_url });
    }
    if (value.overlay_url) {
      volumes.push({
        url: value.overlay_url,
        colormap: 'red',
        opacity: 0.5,
      });
    }
    if (volumes.length > 0) {
      await nv.loadVolumes(volumes);
    }
  }

  $: if (value && nv) loadVolumes();
</script>

<div bind:this={container} class="niivue-container">
  <canvas></canvas>
</div>

<style>
  .niivue-container {
    width: 100%;
    height: 500px;
    background: #000;
  }
  canvas {
    width: 100%;
    height: 100%;
  }
</style>
```

### Phase 3: Implement Python Backend (2-3 hours)

```python
# backend/gradio_niivue_viewer/__init__.py
from __future__ import annotations
from typing import Any
from gradio.components.base import Component
from gradio.data_classes import FileData, GradioModel

class NiiVueViewerData(GradioModel):
    background_url: str | None = None
    overlay_url: str | None = None

class NiiVueViewer(Component):
    """WebGL NIfTI viewer using NiiVue."""

    data_model = NiiVueViewerData

    def __init__(
        self,
        value: NiiVueViewerData | None = None,
        *,
        label: str | None = None,
        height: int = 500,
        **kwargs,
    ):
        self.height = height
        super().__init__(value=value, label=label, **kwargs)

    def preprocess(self, payload: NiiVueViewerData | None) -> dict[str, Any] | None:
        if payload is None:
            return None
        return {
            "background_url": payload.background_url,
            "overlay_url": payload.overlay_url,
        }

    def postprocess(self, value: dict[str, Any] | None) -> NiiVueViewerData | None:
        if value is None:
            return None
        return NiiVueViewerData(
            background_url=value.get("background_url"),
            overlay_url=value.get("overlay_url"),
        )
```

### Phase 4: Build and Test (2-3 hours)

```bash
# Build the component
cd gradio-niivue-viewer
gradio cc build

# Install locally
pip install -e .

# Test in demo app
python demo/app.py
```

### Phase 5: Integrate into stroke-deepisles-demo (1-2 hours)

Replace `gr.HTML` with the custom component:

```python
# Before (broken)
from stroke_deepisles_demo.ui.viewer import create_niivue_html
viewer = gr.HTML(value="", elem_id="niivue-viewer")
# ... then set viewer.value = create_niivue_html(...)

# After (working)
from gradio_niivue_viewer import NiiVueViewer
viewer = NiiVueViewer(label="Interactive 3D Viewer")
# ... then set viewer.value = {"background_url": dwi_url, "overlay_url": mask_url}
```

---

## Existing References

### Working WebGL Custom Components

1. **[gradio-litmodel3d](https://pypi.org/project/gradio-litmodel3d/)**
   - WebGL Model3D viewer with HDR lighting
   - Source: https://github.com/gradio-app/gradio/tree/main/demo/model3d_component
   - Proof that WebGL works in Custom Components

2. **[gradio-molecule3d](https://pypi.org/project/gradio-molecule3d/)**
   - 3D molecule viewer
   - Uses Three.js (WebGL)

### Gradio Documentation

- [Custom Components in 5 Minutes](https://www.gradio.app/guides/custom-components-in-five-minutes)
- [Gradio Components Documentation](https://www.gradio.app/docs/gradio/components)
- [Custom Component Gallery](https://www.gradio.app/custom-components/gallery)

### NiiVue Resources

- [NiiVue GitHub](https://github.com/niivue/niivue)
- [NiiVue npm](https://www.npmjs.com/package/@niivue/niivue)
- [NiiVue Examples](https://niivue.com/docs/)

---

## Acceptance Criteria

### Must Have (MVP)

- [ ] Component loads NIfTI volumes from Gradio file URLs
- [ ] Component displays background image (DWI)
- [ ] Component displays overlay mask (segmentation) with colormap
- [ ] Component works on HuggingFace Spaces
- [ ] No "Loading..." hang - failures are graceful
- [ ] All existing tests pass

### Nice to Have (Future)

- [ ] Crosshair controls
- [ ] Slice orientation toggle (axial/coronal/sagittal)
- [ ] Opacity slider for overlay
- [ ] Pan/zoom/rotate controls
- [ ] Screenshot/export functionality
- [ ] Publish to PyPI for community use

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Svelte/TypeScript learning curve | Follow gradio-litmodel3d example closely |
| NiiVue WebGL2 browser support | NiiVue handles fallbacks internally |
| Build system complexity | Use gradio cc tooling, don't customize |
| HF Spaces static file serving | Component bundles NiiVue, no external deps |

---

## Alternatives Considered

### Alternative 1: Keep Hacking gr.HTML
- **Effort:** Low
- **Success probability:** 0% (CONFIRMED FAILED)
- **Why rejected:** We tried 6 approaches over 2 days. ALL failed. This is not a viable path.

### Alternative 2: Static HTML Space (No Gradio)
- **Effort:** High (rebuild entire UI)
- **Success probability:** 99%
- **Why rejected:** Lose Gradio's file upload, dropdowns, layout features. Too much work.

### Alternative 3: Remove 3D Viewer (2D Only)
- **Effort:** Low
- **Success probability:** 100%
- **Why rejected:** Loses key feature. Static Report tab already works, but 3D is valuable.

---

## Decision

**Proceed with Gradio Custom Component approach.**

This is the official Gradio-recommended solution. It's more work than hacking `gr.HTML`, but it's the architecturally correct approach with 90% success probability vs 30%.

---

## Next Steps

1. [ ] Senior review of this spec
2. [ ] Create `gradio-niivue-viewer` repository (or subdirectory)
3. [ ] Scaffold component with `gradio cc create`
4. [ ] Implement Svelte frontend
5. [ ] Implement Python backend
6. [ ] Test locally
7. [ ] Test on HF Spaces
8. [ ] Integrate into stroke-deepisles-demo
9. [ ] (Optional) Publish to PyPI

---

## Appendix: Why WebGL + Gradio is Hard

From the ROOT_CAUSE_ANALYSIS.md and GRADIO_WEBGL_ANALYSIS.md research:

1. **Gradio closed NIfTI support** (Issue #4511) - "Not planned"
2. **Gradio closed WebGL canvas** (Issue #7649) - "Not planned"
3. **gr.HTML strips script tags** - Security feature
4. **js_on_load + import() blocks hydration** - Proven by A/B test
5. **HF Spaces CSP blocks external CDNs** - No workaround for cdn imports
6. **Gradio maintainer recommendation**: Custom Components

The pattern is clear: **Gradio doesn't natively support custom WebGL in gr.HTML.** The Custom Component is the only officially supported path.
