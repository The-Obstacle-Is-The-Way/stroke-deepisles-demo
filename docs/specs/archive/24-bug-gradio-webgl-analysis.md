# Bug #24: Gradio + WebGL/NiiVue Root Cause Analysis

**Date:** 2025-12-10
**Status:** ALL `gr.HTML` HACKS FAILED - Custom Component Required
**Issue:** HF Spaces stuck on "Loading..." forever
**Root Cause:** The `gr.HTML` + `js_on_load` + async `import()` pattern blocks Svelte hydration
**Note:** Gradio CAN do WebGL via Custom Components (proven by gradio-litmodel3d)
**Solution:** Build Gradio Custom Component (see spec #28)

---

## CONFIRMED: All gr.HTML Hacks Have Failed

| Attempt | Date | Result |
|---------|------|--------|
| CDN import in js_on_load | Dec 9 | FAILED - CSP blocks external imports |
| Vendored + dynamic import() in js_on_load | Dec 9 | FAILED - Blocks Svelte hydration |
| head_paths with loader HTML | Dec 9 | FAILED - Same hydration issue |
| head= with inline import() | Dec 10 | **FAILED** - Confirmed DOA |

**There is no hack that works.** The only path forward is spec #28 (Gradio Custom Component).

---

## Why Are We Using Gradio?

**What Gradio provides:**
- Quick ML demo UIs with Python only (no frontend code needed)
- Built-in components: file upload, sliders, dropdowns, image display
- Easy deployment to HuggingFace Spaces
- Handles backend/frontend communication automatically

**What Gradio does NOT provide:**
- Native support for NIfTI/DICOM medical imaging (closed as "not planned" - [Issue #4511](https://github.com/gradio-app/gradio/issues/4511))
- Native WebGL canvas component (closed as "not planned" - [Issue #7649](https://github.com/gradio-app/gradio/issues/7649))
- Clean way to embed custom WebGL libraries like NiiVue

---

## The Root Cause: We're Fighting `gr.HTML`, Not Gradio

### What We're Trying To Do
Embed NiiVue (a WebGL2 library) into `gr.HTML` using JavaScript.

### Why `gr.HTML` + JavaScript Doesn't Work
1. **`gr.HTML` strips `<script>` tags** - Security feature
2. **`js_on_load` with async `import()` blocks Svelte hydration** - **PROVEN** by A/B test
3. **Our A/B test confirmed**: Disabling `js_on_load` makes the app load perfectly
4. **`head=` parameter with `import()`** - Same hydration blocking issue

### Gradio CAN Do WebGL
**Important clarification:** Gradio supports WebGL via Custom Components. `gradio-litmodel3d` proves this.

The issue is specifically the `gr.HTML` + `js_on_load` + `import()` pattern, NOT Gradio itself.

### Gradio's Official Stance
From Gradio maintainer Abubakar Abid on Issues #4511 and #7649:
> "We are not planning to include this in the core Gradio library."
> "We've now made it possible for Gradio users to create their own custom components."

**The official answer is: Create a Gradio Custom Component.**

---

## The Four Options (Ranked by Effort)

### Option 1: Keep Hacking `gr.HTML` (Current Approach)
- **Effort:** Low
- **Success probability:** 30%
- **What we're trying:** `head=`, `demo.load(_js=...)`, `gr.Blocks(js=...)`
- **Problem:** Fighting Gradio's architecture

### Option 2: Create a Gradio Custom Component
- **Effort:** Medium (2-3 days)
- **Success probability:** 90%
- **What it is:** A proper Svelte + Python component that wraps NiiVue
- **Why it works:** This is the official Gradio way to add WebGL
- **Resources:**
  - [Custom Components Guide](https://www.gradio.app/guides/custom-components-in-five-minutes)
  - [gradio-litmodel3d](https://pypi.org/project/gradio-litmodel3d/) - Example WebGL custom component
  - [Custom Components Gallery](https://www.gradio.app/custom-components/gallery)

### Option 3: Static HTML Space (No Gradio)
- **Effort:** High (rebuild entire UI)
- **Success probability:** 99%
- **What it is:** Pure HTML/CSS/JS app on HF Spaces
- **Why it works:** WebGL works perfectly (Unity, Three.js examples exist)
- **Downside:** Lose Gradio's nice features (file upload UX, etc.)

### Option 4: 2D Slice Fallback (Remove NiiVue Entirely)
- **Effort:** Low
- **Success probability:** 100%
- **What it is:** Use Matplotlib 2D slices instead of 3D WebGL viewer
- **Why it works:** Already works (Static Report tab)
- **Downside:** No interactive 3D visualization

---

## Comparison: Custom Component vs Static HTML

| Aspect | Custom Component | Static HTML |
|--------|------------------|-------------|
| Keep Gradio features | Yes | No |
| File upload UX | Built-in | Must build |
| Sliders/dropdowns | Built-in | Must build |
| HF Spaces deployment | Works | Works |
| Development time | 2-3 days | 3-5 days |
| Maintainability | Better (Gradio handles updates) | Worse (all custom) |

---

## Recommendation

**If current PR #28 fails:**

1. **First try:** `demo.load(_js=...)` approach (1 hour)
2. **If that fails:** Create a Gradio Custom Component for NiiVue (2-3 days)
3. **Nuclear option:** Static HTML Space or remove 3D viewer entirely

**The Custom Component approach is the "correct" solution** - it's what Gradio maintainers recommend for WebGL content. We've been trying to hack around Gradio instead of working with it.

---

## Existing Work We Can Reference

1. **[gradio-litmodel3d](https://pypi.org/project/gradio-litmodel3d/)** - WebGL Model3D with HDR support
2. **[Unet-nifti-gradio](https://github.com/benjaminirving/Unet-nifti-gradio)** - NIfTI + Gradio integration
3. **[papaya-image-viewer-gradio](https://github.com/gradio-app/gradio/issues/4511)** - Medical imaging viewer mentioned in Issue #4511
4. **[NiiVue docs](https://niivue.com/docs/)** - Official NiiVue integration guide

---

## Answer: "What Does Gradio Unblock?"

**Gradio unblocks:**
- UI/UX components (dropdowns, sliders, file upload, etc.)
- Backend/frontend communication
- Easy HF Spaces deployment
- Python-only development (no JS required for basic apps)

**Gradio does NOT unblock:**
- Custom WebGL content (you need a Custom Component)
- Medical imaging formats (NIfTI, DICOM)
- Advanced JavaScript integrations

**If we go Static HTML:** Yes, we'd have to write all the HTML/CSS/JS ourselves, including file upload handling, UI layout, etc. That's what Gradio provides "for free."

---

## Sources

- [HF Forum: Gradio HTML with JS](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)
- [Gradio Issue #4511: 3D Medical Images](https://github.com/gradio-app/gradio/issues/4511)
- [Gradio Issue #7649: WebGL Canvas](https://github.com/gradio-app/gradio/issues/7649)
- [Gradio Custom Components Guide](https://www.gradio.app/guides/custom-components-in-five-minutes)
- [HF Unity WebGL Template](https://github.com/huggingface/Unity-WebGL-template-for-Hugging-Face-Spaces)
