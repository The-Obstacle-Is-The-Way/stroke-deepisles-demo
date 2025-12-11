# NiiVue + Gradio Integration: POSTMORTEM

**Date:** 2025-12-10
**Status:** ABANDONED
**Time Spent:** 2+ days
**Result:** IMPOSSIBLE with current Gradio architecture

---

## The Problem

We needed to display NiiVue (a WebGL-based neuroimaging viewer) inside a Gradio application deployed on HuggingFace Spaces. NiiVue requires JavaScript execution to initialize WebGL and render volumes.

**Gradio does not reliably support JavaScript execution in HTML components.**

---

## Every Approach We Tried

### 1. gr.HTML with Inline `<script>` Tags

**What we did:** Put `<script type="module">` inside gr.HTML value

**Result:** FAILED

**Why:** Browsers do not execute `<script>` tags inserted via innerHTML. This is a browser security feature. Gradio uses innerHTML to update gr.HTML components.

**Source:** [HuggingFace Forum](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)

---

### 2. js_on_load Parameter with Dynamic import()

**What we did:** Used `gr.HTML(js_on_load=...)` with `await import('niivue')`

**Result:** FAILED

**Why:** The async `import()` blocks Gradio's Svelte hydration process. The entire UI freezes on "Loading..." forever.

**Evidence:** A/B test confirmed: disabling js_on_load made the app load perfectly.

---

### 3. head= Parameter on gr.Blocks() (Gradio 5 syntax)

**What we did:** `gr.Blocks(head='<script>...</script>')`

**Result:** FAILED

**Why:** This is Gradio 5 syntax. In Gradio 6, head= moved to launch().

---

### 4. head= Parameter on launch() with import()

**What we did:** `demo.launch(head='<script type="module">await import(...)</script>')`

**Result:** FAILED

**Why:** Same problem as #2 - async import() still blocks hydration even when in head.

---

### 5. head_paths= Parameter

**What we did:** Used `head_paths=['path/to/script.js']`

**Result:** FAILED

**Why:** Files weren't served correctly, same hydration blocking issues.

---

### 6. Vendored NiiVue (Local File)

**What we did:** Downloaded niivue.js locally to bypass CDN/CSP issues

**Result:** PARTIALLY WORKED (file served) but FAILED (still blocks hydration)

**Why:** The file serving worked, but the async import() pattern still blocked Svelte hydration.

---

### 7. Custom Svelte Component (packages/niivueviewer/)

**What we did:** Built a full Gradio custom component with Svelte 5 and NiiVue bundled via npm

**Result:** FAILED - Froze entire UI

**Issues encountered:**
- Missing `gradio` prop for StatusTracker i18n
- Missing `packages/` directory in Docker build
- Templates not being served correctly
- Even after fixes, UI completely frozen

**Time spent:** ~1 day on this approach alone

---

### 8. gradio-iframe Package

**What we did:** Attempted to use `gradio-iframe` package to isolate NiiVue in an iframe

**Result:** FAILED - Incompatible with Gradio 6

**Why:** `gradio-iframe` hasn't been updated since Jan 2024. Installing it forces Gradio downgrade from 6.x to 4.x.

---

### 9. Inline iframe via gr.HTML (NOT FULLY TESTED)

**What we did:** Considered using `gr.HTML('<iframe src="..."></iframe>')`

**Result:** NOT TESTED - 50/50 chance of working

**Why:** We stopped here because:
- No definitive evidence it works on HF Spaces
- CSP may still block JavaScript in iframes
- Would be yet another gamble after 2 days of failures

---

## Root Causes

### 1. Gradio's innerHTML Security Model

Gradio uses innerHTML to update component values. Browsers intentionally do not execute `<script>` tags inserted via innerHTML. This is a security feature, not a bug.

### 2. Svelte Hydration Blocking

Any async JavaScript execution during Gradio's component mounting phase can block Svelte hydration, causing the entire UI to freeze.

### 3. HuggingFace Spaces CSP

HF Spaces has Content Security Policy headers that can block external CDN imports and certain JavaScript execution patterns.

### 4. Gradio's Design Philosophy

Gradio is designed for simple input/output ML demos, not complex WebGL applications with their own JavaScript lifecycle. The Gradio maintainers explicitly closed requests for WebGL/NIfTI support:
- [Issue #4511](https://github.com/gradio-app/gradio/issues/4511) - NIfTI support: "Not planned"
- [Issue #7649](https://github.com/gradio-app/gradio/issues/7649) - WebGL canvas: "Not planned"

Their answer: "Build a custom component" - which we tried and failed.

---

## What Actually Works on HF Spaces

**Everything EXCEPT NiiVue:**
- Gradio UI loads correctly
- Dropdowns, buttons, checkboxes work
- DeepISLES segmentation pipeline runs (~38 seconds)
- Matplotlib plots render correctly
- JSON metrics display works
- File downloads work

**The ONLY broken thing:** NiiVue JavaScript execution

---

## Reference Implementation

The only working NiiVue + HF Spaces example we found:
- [TobiasPitters/bids-neuroimaging](https://huggingface.co/spaces/TobiasPitters/bids-neuroimaging)
- **Does NOT use Gradio** - uses FastAPI with raw HTML
- Scripts execute because they're in the actual HTML document, not injected via innerHTML

---

## Conclusion

**Gradio is fundamentally incompatible with NiiVue (or any WebGL library requiring JavaScript execution).**

The only viable paths forward:
1. **Remove NiiVue** - Keep 2D Matplotlib visualizations only
2. **Abandon Gradio** - Rewrite with FastAPI + raw HTML
3. **Wait for Gradio** - Maybe someday they'll add proper JS support (unlikely based on closed issues)

---

## Files in Archive

All detailed debugging specs are preserved in `docs/specs/archive/`:
- `24-bug-hf-spaces-loading-forever.md` - CSP and hydration analysis
- `28-gradio-custom-component-niivue.md` - Custom component attempt
- `29-codebase-status-audit.md` - Code audit
- `32-bug-hf-spaces-ui-frozen-audit.md` - UI freeze investigation
- `33-definitive-niivue-gradio-integration.md` - Integration research
- `34-COMPREHENSIVE-NIIVUE-GRADIO-AUDIT.md` - Final comprehensive audit
- And others documenting the full journey

---

## Lessons Learned

1. **Gradio is not a general-purpose web framework** - It's designed for simple ML demos
2. **JavaScript execution in Gradio is fundamentally broken** - innerHTML security model prevents it
3. **"Workarounds" don't work** - js_on_load, head=, custom components all fail
4. **Community packages may be abandoned** - gradio-iframe hasn't been updated for Gradio 6
5. **Read the closed issues first** - Gradio maintainers already said "not planned" for WebGL

---

## Final Status

**NiiVue integration: ABANDONED**

The app works on HF Spaces with 2D Matplotlib visualizations. The 3D NiiVue viewer is not possible with Gradio.

If 3D visualization is required in the future, Gradio must be replaced entirely.
