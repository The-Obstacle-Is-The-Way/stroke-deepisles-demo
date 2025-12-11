# NiiVue + Gradio Integration: POSTMORTEM

**Date:** 2025-12-10
**Status:** ABANDONED
**Time Spent:** 2+ days
**Result:** IMPOSSIBLE with current Gradio architecture

---

## Executive Summary

We attempted to integrate NiiVue (a WebGL-based neuroimaging viewer) into a Gradio application deployed on HuggingFace Spaces. After exhaustive investigation across 10+ approaches, we conclusively determined that **Gradio is fundamentally incompatible with NiiVue or any JavaScript library requiring reliable execution**.

---

## Stack Versions

| Component | Version |
|-----------|---------|
| Python | 3.12 |
| Gradio | >=6.0.0,<7.0.0 |
| NiiVue | 0.65.0 (vendored) |
| Svelte (custom component) | ^5.43.4 |
| @gradio/preview | 0.15.1 |
| HuggingFace Spaces | Docker SDK |

---

## The Problem

We needed to display NiiVue inside a Gradio app on HF Spaces. NiiVue requires JavaScript execution to initialize WebGL and render volumes.

**Gradio does not reliably support JavaScript execution in HTML components.**

---

## All Approaches Tried

### 1. gr.HTML with Inline `<script>` Tags

**What we did:** Put `<script type="module">` inside gr.HTML value

**Result:** FAILED

**Why:** Browsers do not execute `<script>` tags inserted via innerHTML. This is a browser security feature, not a bug. Gradio uses innerHTML to update gr.HTML components.

**Source:** [HuggingFace Forum](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)

---

### 2. js_on_load Parameter with Dynamic import()

**What we did:** Used `gr.HTML(js_on_load=...)` with async IIFE containing `await import('niivue')`

**Result:** FAILED

**Why:** The async `import()` blocks Gradio's Svelte hydration process. The entire UI freezes on "Loading..." forever.

**Evidence:** A/B test confirmed - disabling js_on_load made the app load perfectly. All other features (DeepISLES pipeline, Matplotlib, Metrics) worked.

**Technical Detail:** `js_on_load` only runs ONCE when the component first mounts. When `gr.HTML` value updates (after segmentation), js_on_load does NOT re-run. The HTML updates but JavaScript initialization never happens again.

**Source:** [Gradio Custom HTML Components Guide](https://www.gradio.app/guides/custom_HTML_components) - "Event listeners attached in js_on_load are only attached once when the component is first rendered."

---

### 3. .then(fn=None, js=...) Pattern

**What we did:** Tried using `.then(fn=None, js=NIIVUE_UPDATE_JS)` on event handlers

**Result:** FAILED

**Why:** The `js` parameter in event handlers has a completely different context than `js_on_load`:
- `js_on_load` has access to `element` (the DOM element)
- `js` on event handlers only receives input/output VALUES, not DOM elements
- Must use `document.querySelector()` instead of `element.querySelector()`
- The async import() still blocked hydration

**Source:** [GitHub Issue #6729](https://github.com/gradio-app/gradio/issues/6729) - `js` without `fn` only executes if `fn` is explicitly set to `None`

---

### 4. head= Parameter on gr.Blocks() (Gradio 5 Syntax)

**What we did:** `gr.Blocks(head='<script>...</script>')`

**Result:** FAILED

**Why:** This is Gradio 5 syntax. In Gradio 6, `head=`, `js=`, `css=` moved from `gr.Blocks()` to `launch()`.

**Source:** [Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)

---

### 5. head= Parameter on launch() with import()

**What we did:** `demo.launch(head='<script type="module">await import(...)</script>')`

**Result:** FAILED

**Why:** Same problem as #2 - async import() still blocks hydration even when in `<head>`.

**Additional Issue:** [GitHub Issue #10250](https://github.com/gradio-app/gradio/issues/10250) documents that JavaScript in `head` param has non-deterministic execution - "would sometimes execute only after extended waiting periods (5+ minutes), or occasionally not at all."

---

### 6. head_paths= Parameter

**What we did:** Used `head_paths=['path/to/niivue-loader.html']`

**Result:** FAILED

**Why:** Multiple issues:
- Files weren't served correctly without `gr.set_static_paths()`
- [GitHub Issue #11649](https://github.com/gradio-app/gradio/issues/11649) - head= with file paths causes 404
- Even when files served correctly, the async import() pattern still blocked hydration

---

### 7. Vendored NiiVue (Local File)

**What we did:** Downloaded niivue.js (2.9MB) locally to bypass CDN/CSP issues

**Result:** PARTIALLY WORKED (file served) but FAILED (still blocks hydration)

**Why:** The file serving worked via `allowed_paths` and `gr.set_static_paths()`, but the async import() pattern still blocked Svelte hydration.

**Secondary Issue:** Base64 payload risk - encoding DWI (~30MB) + ADC (~18MB) as base64 would create ~65MB payloads, risking browser memory issues and Gradio payload limits.

---

### 8. Head Script + MutationObserver Pattern

**What we did:** Load NiiVue via `launch(head=...)` globally, then use MutationObserver to watch for DOM changes and trigger initialization

**Result:** FAILED

**Why:** The head script still uses `await import()` which blocks hydration. Even if NiiVue loads globally as `window.Niivue`, the async pattern during page load still freezes the UI.

**What it should have done:** MutationObserver watches for `data-*` attribute changes on gr.HTML elements, then calls `initNiiVue()`. But the initial import never completes due to hydration blocking.

---

### 9. Custom Svelte Component (packages/niivueviewer/)

**What we did:** Built a full Gradio custom component:
- Svelte 5 frontend with NiiVue bundled via npm (`@niivue/niivue@0.65.0`)
- Python backend component class
- StatusTracker for loading states
- Templates compiled via `gradio cc build`

**Result:** FAILED - Froze entire UI

**Issues encountered:**

| Issue | Description | Fix Applied | Still Broken |
|-------|-------------|-------------|--------------|
| Missing `gradio` prop | StatusTracker requires `gradio.i18n` for translations | PR #31 added it | Yes |
| Missing packages/ in Docker | Dockerfile didn't copy `packages/` directory | PR #30 added COPY | Yes |
| style.css 404 | [Issue #7026](https://github.com/gradio-app/gradio/issues/7026) - causes loading hang | N/A | Yes |
| CJS/ESM conflicts | [Issue #6087](https://github.com/gradio-app/gradio/issues/6087) - dev server stuck | N/A | Yes |
| Templates undefined | [Issue #9879](https://github.com/gradio-app/gradio/issues/9879) | N/A | Yes |

**Time spent:** ~1 day on this approach alone

**Root cause unresolved:** Even after adding `gradio` prop and shipping templates, UI still completely frozen. The exact failure mode remains unknown.

**Gradio team's stance on custom components:**
- [Issue #12074](https://github.com/gradio-app/gradio/issues/12074) - Proposed `gr.Custom` class because custom components are "too complex"
- Custom components have multiple fragile failure modes that make them riskier than simpler approaches

---

### 10. gradio-iframe Package

**What we did:** Attempted to use `gradio-iframe` package to isolate NiiVue in an iframe

**Result:** FAILED - Incompatible with Gradio 6

**Why:** `gradio-iframe` version 0.0.10 (Jan 2024) is the latest. Installing it forces Gradio downgrade from 6.x to 4.x. Package is effectively abandoned.

**Source:** [PyPI gradio-iframe](https://pypi.org/project/gradio-iframe/)

---

### 11. Inline iframe via gr.HTML (NOT TESTED)

**What we planned:** Use `gr.HTML('<iframe src="..."></iframe>')` with standalone viewer HTML

**Result:** PLANNED BUT NOT EXECUTED

**Why we stopped:** After 2+ days of failures, we stopped here because:
- No definitive evidence it works on HF Spaces
- CSP may still block JavaScript in iframes
- 50/50 chance of working - yet another gamble

**This remains the only untested approach** that might theoretically work.

---

## Root Causes

### 1. Gradio's innerHTML Security Model

Gradio uses innerHTML to update component values. Browsers intentionally do not execute `<script>` tags inserted via innerHTML. This is a security feature, not a bug.

**Implication:** Any approach that relies on Gradio updating HTML content cannot include executable JavaScript.

### 2. Svelte Hydration Blocking

Any async JavaScript execution during Gradio's component mounting phase can block Svelte hydration, causing the entire UI to freeze.

**Specifically:** `<script type="module">` with `import()` statements - even deferred - can interfere with Svelte's initialization timing in unpredictable ways.

### 3. HuggingFace Spaces CSP

HF Spaces has Content Security Policy headers that block external CDN imports:
- `script-src 'self' 'unsafe-inline' 'unsafe-eval'` (estimated)
- External domains like unpkg.com are blocked
- CSP headers are NOT customizable per HF documentation

**Source:** [HF Spaces Config Reference](https://huggingface.co/docs/hub/spaces-config-reference)

### 4. js_on_load Only Runs Once

Gradio's `js_on_load` executes only when the component first mounts, not when the value updates. This breaks any approach that needs to reinitialize JavaScript after data changes.

### 5. Module Script Timing Race Condition

`<script type="module">` is deferred by default. It executes AFTER HTML parsing but the timing relative to Svelte component mounting is unpredictable. `window.Niivue` may be undefined when `js_on_load` tries to access it.

### 6. Two Entry Points with Path Mismatch Risk

Root `app.py` vs `src/.../ui/app.py` compute asset paths differently:
- Root: `Path(__file__).parent / "src" / "..." / "assets"`
- Module: `Path(__file__).parent / "assets"`

Docker uses `python -m stroke_deepisles_demo.ui.app`, so only the module path matters, but this caused confusion during debugging.

### 7. Gradio's Design Philosophy

Gradio is designed for simple input/output ML demos, not complex WebGL applications with their own JavaScript lifecycle. The Gradio maintainers explicitly closed requests for WebGL/NIfTI support:

| Issue | Request | Response |
|-------|---------|----------|
| [#4511](https://github.com/gradio-app/gradio/issues/4511) | NIfTI/3D medical image support | "Not planned" - told to build custom component |
| [#7649](https://github.com/gradio-app/gradio/issues/7649) | WebGL Canvas component | "Not planned" - "too niche" |

---

## GitHub Issues Referenced

### WebGL/3D Related

| Issue | Description | Status |
|-------|-------------|--------|
| [#4511](https://github.com/gradio-app/gradio/issues/4511) | 3D medical image support | Closed - "use custom component" |
| [#7649](https://github.com/gradio-app/gradio/issues/7649) | WebGL Canvas component | Closed - "too niche" |
| [#5765](https://github.com/gradio-app/gradio/issues/5765) | Model3D rendered see-through | WebGL error |
| [#7632](https://github.com/gradio-app/gradio/issues/7632) | Model3D collapsed in tabs | Open |
| [#7485](https://github.com/gradio-app/gradio/issues/7485) | Model3D not working when embedded | Open |

### Custom Component Related

| Issue | Description | Impact |
|-------|-------------|--------|
| [#7026](https://github.com/gradio-app/gradio/issues/7026) | style.css 404 causes hang | Loading forever |
| [#6087](https://github.com/gradio-app/gradio/issues/6087) | CJS imports break dev server | Dev stuck |
| [#9879](https://github.com/gradio-app/gradio/issues/9879) | Templates undefined | Component fails |
| [#12074](https://github.com/gradio-app/gradio/issues/12074) | Custom components too complex | Proposed gr.Custom |

### JavaScript Loading Related

| Issue | Description | Status |
|-------|-------------|--------|
| [#11649](https://github.com/gradio-app/gradio/issues/11649) | head= with files causes 404 | Closed - use head_paths |
| [#10250](https://github.com/gradio-app/gradio/issues/10250) | head JS execution non-deterministic | Open |
| [#6426](https://github.com/gradio-app/gradio/issues/6426) | head argument bugs | Fixed in PR #6639 |
| [#6729](https://github.com/gradio-app/gradio/issues/6729) | js without fn requires explicit None | Closed |

### HF Spaces SSE/Queue Related

| Issue | Description | Impact |
|-------|-------------|--------|
| [#5974](https://github.com/gradio-app/gradio/issues/5974) | Stuck in processing with queue | Loading forever |
| [#4279](https://github.com/gradio-app/gradio/issues/4279) | Stuck on Loading with new Gradio | Loading forever |
| [#4332](https://github.com/gradio-app/gradio/issues/4332) | Loading stuck in non-internet env | SSE connection issues |

---

## What Actually Works on HF Spaces

**Proof from 2025-12-11 HF Spaces test** (after removing custom component):

| Component | Status |
|-----------|--------|
| Gradio UI | ✅ WORKS - App loads, no freeze |
| Dropdown | ✅ WORKS - Case selector shows 149 cases |
| Buttons | ✅ WORKS - "Run Segmentation" triggers pipeline |
| DeepISLES Pipeline | ✅ WORKS - Runs in ~38 seconds |
| Matplotlib Plots | ✅ WORKS - Static Report renders correctly |
| Metrics JSON | ✅ WORKS - Displays dice_score, volume_ml |
| File Downloads | ✅ WORKS - Prediction NIfTI downloadable |
| NiiVue Viewer | ❌ BROKEN - Shows placeholder, script never executes |

**This proves:** The custom Svelte component WAS the cause of the UI freeze. Everything else in the stack works perfectly.

---

## Reference Implementation

The only working NiiVue + HF Spaces example:
- [TobiasPitters/bids-neuroimaging](https://huggingface.co/spaces/TobiasPitters/bids-neuroimaging)
- **Does NOT use Gradio** - uses FastAPI with raw HTML
- Scripts execute because they're in the actual HTML document, not injected via innerHTML
- Uses NiiVue 0.57.0

---

## Viable Paths Forward

### Option 1: Remove NiiVue (IMPLEMENTED)

Keep 2D Matplotlib visualizations only. This is what we shipped.

**Pros:** Works reliably, no JavaScript complexity
**Cons:** No 3D interactivity

### Option 2: Abandon Gradio

Rewrite with FastAPI + raw HTML, like the reference implementation.

**Pros:** Full control over JavaScript execution
**Cons:** Lose all Gradio benefits (state, components, themes, HF integration)

### Option 3: Inline iframe (UNTESTED)

Use `gr.HTML('<iframe src="..."></iframe>')` with standalone viewer HTML.

**Pros:** Might work - iframes are isolated
**Cons:** Untested, CSP may still block, communication is complex

### Option 4: Wait for Gradio gr.Custom

[Issue #12074](https://github.com/gradio-app/gradio/issues/12074) proposes simpler custom components.

**Pros:** Might solve our issues
**Cons:** No timeline, may never happen

---

## Lessons Learned

1. **Gradio is not a general-purpose web framework** - It's designed for simple ML demos, not complex WebGL applications

2. **JavaScript execution in Gradio is fundamentally broken** - innerHTML security model prevents script execution

3. **js_on_load has severe limitations** - Only runs once, async IIFEs can block hydration, no access to `element` in .then(js=) handlers

4. **"Workarounds" don't work** - js_on_load, head=, head_paths=, MutationObserver, custom components - all fail

5. **Custom components are fragile** - Multiple failure modes (templates, i18n props, build artifacts) make them risky

6. **Community packages may be abandoned** - gradio-iframe hasn't been updated for Gradio 6

7. **Read the closed issues first** - Gradio maintainers already said "not planned" for WebGL

8. **Use `data-*` attributes for state** - gr.HTML re-renders completely on update, so data attributes are the only reliable way to pass information to JavaScript

9. **Two entry points = confusion** - Root app.py vs module app.py compute paths differently, causing debugging overhead

10. **The only untested path is inline iframe** - If we ever revisit this, start there

---

## Final Status

**NiiVue integration: ABANDONED**

The app works on HF Spaces with 2D Matplotlib visualizations. The 3D NiiVue viewer is not possible with Gradio.

If 3D visualization is required in the future:
1. Try inline iframe approach first (untested)
2. If that fails, Gradio must be replaced entirely with FastAPI + raw HTML

---

## Archive Note

This postmortem consolidates all findings from the following archived specs:
- `00-context.md` - Project context
- `10-bug-niivue-viewer-black-screen.md` - Initial black screen investigation
- `11-bug-niivue-js-on-load-not-rerunning.md` - js_on_load limitations
- `19-perf-base64-to-file-urls.md` - Base64 payload optimization
- `24-bug-hf-spaces-loading-forever.md` - CSP and hydration analysis
- `24-bug-gradio-webgl-analysis.md` - WebGL analysis
- `28-gradio-custom-component-niivue.md` - Custom component attempt
- `29-codebase-status-audit.md` - Code audit
- `30-bug-hf-spaces-build-packages-dir.md` - Docker build fix
- `32-bug-hf-spaces-ui-frozen-audit.md` - UI freeze investigation
- `33-definitive-niivue-gradio-integration.md` - Integration research
- `34-COMPREHENSIVE-NIIVUE-GRADIO-AUDIT.md` - Final comprehensive audit
- `35-FINAL-ATTEMPT-GRADIO-IFRAME.md` - gradio-iframe attempt (not executed)
- `AUDIT_JS_LOADING_ISSUES.md` - JavaScript loading audit
- `DIAGNOSTIC_HF_LOADING.md` - HF loading diagnostics
- `ROOT_CAUSE_ANALYSIS.md` - Root cause analysis

The archive can be deleted now that this postmortem is complete.
