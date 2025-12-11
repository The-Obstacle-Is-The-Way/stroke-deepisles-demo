# HF Spaces UI Completely Broken - Consolidated Audit

**Date:** 2025-12-10
**Branch:** `debug/hf-spaces-ui-completely-broken`
**Status:** P0 CRITICAL - ROOT CAUSE IDENTIFIED + EXTERNALLY VALIDATED

---

## TL;DR - THE FIXES (2 Critical Issues)

### Issue 1: Missing `gradio` Prop (Causes UI Freeze)

Our custom component is missing the **`gradio` prop** which provides `i18n` and `autoscroll`. This is 100% required for StatusTracker to work.

**Current broken code:**
```svelte
// WRONG - missing gradio prop
let { value, loading_status, ... }: Props = $props();

<StatusTracker {...loading_status} />  // CRASHES - no i18n!
```

**Correct pattern:**
```svelte
// CORRECT - includes gradio prop (can use $props() OR export let)
import type { Gradio } from "@gradio/utils";

let { gradio, loading_status, ... }: Props = $props();

<StatusTracker
    autoscroll={gradio.autoscroll}
    i18n={gradio.i18n}
    {...loading_status}
/>
```

### Issue 2: .gitignore Excludes Compiled Templates (Causes Missing Assets on HF Spaces)

**CRITICAL NEW FINDING from external validation:**

`packages/niivueviewer/.gitignore` line 12 has:
```
backend/**/templates/
```

This means **any rebuilt component templates will NOT be committed**. Even though the current templates are tracked (added before the rule), a `gradio cc build` will create new files that Git ignores.

**Fix:** Remove `backend/**/templates/` from `.gitignore`

---

## Root Cause (CONFIRMED)

### Primary Issue: Missing `gradio` Prop

The custom component **does not declare the `gradio` prop**, which is injected by the parent Gradio application and contains:
- `gradio.i18n` - **REQUIRED** by StatusTracker for text formatting
- `gradio.autoscroll` - Controls scroll behavior
- `gradio.dispatch()` - For emitting events

**Evidence:**
- [Gradio Frontend Guide](https://www.gradio.app/guides/frontend) explicitly shows `gradio` prop is required
- [PDF Component Example](https://www.gradio.app/guides/pdf-component-example) shows working pattern
- [StatusTracker npm](https://www.npmjs.com/package/@gradio/statustracker) confirms `i18n` is required

### Secondary Issue: Svelte 5 Runes vs Svelte 4 Syntax - **REFUTED**

**External validation clarified:** Svelte 5 runes are NOT inherently risky.

Gradio 6 ships with **Svelte 5.43.14**, and `@gradio` packages peer-depend on `svelte ^5.43.4`. Svelte 5 runes (`$props()`, `$effect()`) are supported.

| File | Syntax | Status |
|------|--------|--------|
| Index.svelte | `$props()` (Svelte 5) | **OK** (if gradio prop is added) |
| Example.svelte | `export let` (Svelte 4) | OK (legacy syntax) |
| Gradio PDF example | `export let` (Svelte 4) | Reference (uses older syntax) |

**Verdict:** We can keep `$props()` and `$effect()`. The issue is the missing `gradio` prop, not the syntax choice. However, mixing paradigms within a single package (Index uses runes, Example uses legacy) is inconsistent and should be unified.

---

## All Issues Found (Priority Order) - EXTERNALLY VALIDATED

### P0 - Critical (Will Definitely Break)

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| 1 | **Missing `gradio` prop** | Index.svelte:8-20 | Add `gradio: Gradio<{...}>` to Props interface and destructure |
| 2 | **Missing `i18n` to StatusTracker** | Index.svelte:120-123 | Add `i18n={gradio.i18n}` |
| 3 | **Missing `autoscroll` to StatusTracker** | Index.svelte:120-123 | Replace `autoscroll={false}` with `autoscroll={gradio.autoscroll}` |
| 4 | **`.gitignore` excludes templates/** | `.gitignore:12` | Remove `backend/**/templates/` line |

### P1 - Likely Breaking

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| 5 | No error handling in onMount | Index.svelte:40-50 | Wrap NiiVue init in try/catch |
| 6 | Double loadVolumes call (onMount + $effect) | Index.svelte:49,98-103 | Remove $effect's loadVolumes() or add guard |

### P2 - Code Quality (Should Fix)

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| 7 | Unused template dependencies | frontend/package.json | Remove cropperjs, lazy-brush, resize-observer-polyfill |
| 8 | Example.svelte value shape mismatch | Example.svelte | Update to use {background_url, overlay_url} |
| 9 | Mixed Svelte syntax (Index=runes, Example=legacy) | Both files | Unify to one paradigm |

### P3 - Documentation

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| 10 | TECHNICAL_DEBT.md says P0 resolved | docs/TECHNICAL_DEBT.md:13-33 | Update status to reflect unresolved |
| 11 | Stale diagnostic docs | ROOT_CAUSE_ANALYSIS.md, etc | Archive or update |

### NOT an Issue (External Validation Refuted)

| # | Previous Claim | Status | Reason |
|---|----------------|--------|--------|
| - | Svelte 5 runes are risky | **REFUTED** | Gradio 6 ships Svelte 5.43.14; runes are supported |
| - | Missing EVENTS breaks component | **LOW PRIORITY** | Output components can work without EVENTS declaration |

---

## Correct Index.svelte Pattern

Based on [Gradio's PDF Component Example](https://www.gradio.app/guides/pdf-component-example) + external validation that Svelte 5 runes are OK:

```svelte
<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { Niivue } from '@niivue/niivue';
    import { Block } from "@gradio/atoms";
    import { StatusTracker } from "@gradio/statustracker";
    import type { LoadingStatus } from "@gradio/statustracker";
    import type { Gradio } from "@gradio/utils";

    // Props interface - MUST include gradio
    interface Props {
        value?: { background_url: string | null; overlay_url: string | null } | null;
        label?: string;
        show_label?: boolean;
        loading_status?: LoadingStatus;
        elem_id?: string;
        elem_classes?: string[];
        visible?: boolean;
        height?: number;
        container?: boolean;
        scale?: number | null;
        min_width?: number;
        // CRITICAL: gradio prop provides i18n, autoscroll, dispatch
        gradio: Gradio<{ change: never }>;
    }

    // Svelte 5 runes syntax (validated as OK with Gradio 6)
    let {
        value = null,
        label,
        show_label = true,
        loading_status,
        elem_id = "",
        elem_classes = [],
        visible = true,
        height = 500,
        container = true,
        scale = null,
        min_width = undefined,
        gradio  // CRITICAL: must destructure this
    }: Props = $props();

    let canvas: HTMLCanvasElement;
    let nv: Niivue | null = null;
    let initialized = false;  // Guard against double-load

    onMount(async () => {
        try {
            nv = new Niivue({
                backColor: [0, 0, 0, 1],
                show3Dcrosshair: true,
                logging: false
            });
            await nv.attachToCanvas(canvas);
            await loadVolumes();
            initialized = true;
        } catch (error) {
            console.error('[NiiVue] Initialization failed:', error);
        }
    });

    onDestroy(() => {
        if (nv) {
            nv.cleanup();
            nv = null;
        }
    });

    async function loadVolumes() {
        if (!nv) return;

        while (nv.volumes.length > 0) {
            nv.removeVolume(nv.volumes[0]);
        }

        if (!value) {
            nv.drawScene();
            return;
        }

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
        } else {
            nv.drawScene();
        }
    }

    // Svelte 5 $effect - only run after initial mount to avoid double-load
    $effect(() => {
        if (initialized && value !== undefined) {
            loadVolumes();
        }
    });
</script>

<Block
    {visible}
    variant="solid"
    padding={false}
    {elem_id}
    {elem_classes}
    {height}
    allow_overflow={false}
    {container}
    {scale}
    {min_width}
>
    {#if loading_status}
        <StatusTracker
            autoscroll={gradio.autoscroll}
            i18n={gradio.i18n}
            {...loading_status}
        />
    {/if}

    <div class="niivue-container" style="height: {height}px;">
        <canvas bind:this={canvas}></canvas>
    </div>
</Block>

<style>
    .niivue-container {
        width: 100%;
        background: #000;
        position: relative;
        border-radius: var(--radius-lg);
        overflow: hidden;
    }
    canvas {
        width: 100%;
        height: 100%;
        outline: none;
        display: block;
    }
</style>
```

---

## Python Backend Fix (LOW PRIORITY)

**External validation says:** EVENTS is not required for output-only components. The UI freeze is NOT caused by missing EVENTS.

However, if we want to emit events in the future:

```python
from gradio.events import Events

class NiiVueViewer(Component):
    """WebGL NIfTI viewer using NiiVue."""

    EVENTS = [Events.change]  # OPTIONAL - add if we want to emit change events

    data_model = NiiVueViewerData
    # ... rest unchanged
```

**Decision:** Skip for now. Focus on P0 issues first.

---

## Validation Checklist (Updated per External Validation)

### Before Fix
- [ ] `gradio` prop declared? **NO** ← P0
- [ ] `i18n` passed to StatusTracker? **NO** ← P0
- [ ] `autoscroll` passed to StatusTracker? **NO** ← P0
- [ ] `.gitignore` allows templates/? **NO** (ignored!) ← P0
- [ ] onMount has error handling? **NO** ← P1
- [ ] Double loadVolumes prevented? **NO** ← P1

### After Fix (Target)
- [x] `gradio` prop declared? YES
- [x] `i18n` passed to StatusTracker? YES
- [x] `autoscroll` passed to StatusTracker? YES
- [x] `.gitignore` allows templates/? YES
- [x] onMount has error handling? YES
- [x] Double loadVolumes prevented? YES (via `initialized` guard)

### Not Required (Per External Validation)
- Svelte 4 syntax? **NOT REQUIRED** - Svelte 5 runes are OK with Gradio 6
- EVENTS in Python? **NOT REQUIRED** - output components work without it

---

## Test Plan

### Step 1: Local Test
```bash
cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/stroke-deepisles-demo
uv run python -m stroke_deepisles_demo.ui.app
```
Open http://localhost:7860 and verify:
- [ ] Page loads without freezing
- [ ] Dropdown is clickable
- [ ] Buttons respond
- [ ] NiiVue canvas initializes (shows black, not "loading...")

### Step 2: Rebuild Component
```bash
cd packages/niivueviewer
gradio cc build
```

### Step 3: HF Spaces Deploy
Push to HF Spaces only after local test passes.

---

## External Audit Validation (Two Independent Agents Confirmed)

| Claim | Validated | Evidence |
|-------|-----------|----------|
| StatusTracker requires `i18n` | **TRUE** | @gradio/statustracker npm package requires i18n with no default; compiled JS dereferences `e.i18n()` |
| `gradio` prop provides `i18n` | **TRUE** | Official PDF Component Example shows `gradio.i18n` pattern |
| Svelte 5 runes cause issues | **REFUTED** | Gradio 6 ships Svelte 5.43.14; @gradio packages peer-depend on svelte ^5.43.4 |
| Missing EVENTS breaks component | **REFUTED** | Output components can work without EVENTS; not relevant to UI freeze |
| `.gitignore` excludes templates/ | **TRUE** | `packages/niivueviewer/.gitignore:12` has `backend/**/templates/` |
| `demo.load()` blocks hydration | **FALSE** | Runs after render, not the cause |

### Web Search Validation Sources
- Gradio GitHub Issue #6609: Hydration freezes when frontend errors occur before StatusTracker renders
- Gradio GitHub Issue #7649: WebGL must be handled via custom component
- Gradio GitHub Issue #11319: Spaces failures when templates not packaged
- @gradio/statustracker npm tarball: Props interface confirms `i18n` required with no default

---

## References

- [Gradio Frontend Guide](https://www.gradio.app/guides/frontend) - Shows `gradio` prop pattern
- [Gradio PDF Component Example](https://www.gradio.app/guides/pdf-component-example) - Complete working example
- [Gradio Backend Guide](https://www.gradio.app/guides/backend) - EVENTS documentation
- [Gradio StatusTracker npm](https://www.npmjs.com/package/@gradio/statustracker) - Package details
- [Gradio Custom Components](https://www.gradio.app/guides/custom-components-in-five-minutes) - Getting started
- [Gradio i18n](https://www.gradio.app/guides/internationalization) - Internationalization docs

---

## Files to Modify

| File | Change |
|------|--------|
| `packages/niivueviewer/frontend/Index.svelte` | Rewrite with `gradio` prop, Svelte 4 syntax |
| `packages/niivueviewer/backend/gradio_niivueviewer/niivueviewer.py` | Add `EVENTS = [Events.change]` |

---

## WHY WAS THIS MISSED? (Root Cause of Root Cause)

### The Spec Itself Was Incomplete

**Spec #28** (`docs/specs/28-gradio-custom-component-niivue.md`) provided implementation guidance that **did not include the `gradio` prop**. Looking at lines 176-296 of the spec:

```svelte
// What the spec showed (WRONG):
export let value: {...} | null = null;
// ... custom loading/error divs
// NO gradio prop
// NO StatusTracker
```

The spec **did NOT read the official Gradio Frontend Guide thoroughly**. It showed custom loading/error handling instead of using Gradio's official `StatusTracker` component.

### The Implementation Improved On The Spec (But Still Wrong)

The actual implementation in `Index.svelte` **correctly** chose to use:
- `Block` component wrapper (correct)
- `StatusTracker` component (correct approach)

But then **didn't research what StatusTracker requires**:
- Missing `gradio` prop declaration
- Missing `i18n={gradio.i18n}`
- Missing `autoscroll={gradio.autoscroll}`

### The Fundamental Failure

| Stage | What Happened | What Should Have Happened |
|-------|---------------|---------------------------|
| Spec Writing | Read "Custom Components in 5 Minutes" | Read FULL Frontend Guide + PDF Example |
| Spec Review | Focused on NiiVue/WebGL integration | Verified against working Gradio components |
| Implementation | Used StatusTracker without research | Checked StatusTracker npm package requirements |
| Testing | Tested locally (worked) | Should have checked browser console for errors |

---

## The Correct Prompting Approach (For Future Reference)

### What We Asked
```
Create a Gradio Custom Component for NiiVue WebGL viewer
```

### What We Should Have Asked

```markdown
## Task: Create a Gradio Custom Component for NiiVue

### BEFORE writing ANY code:

1. **READ these official Gradio docs IN FULL** (not skimming):
   - https://www.gradio.app/guides/frontend (CRITICAL - shows gradio prop)
   - https://www.gradio.app/guides/pdf-component-example (working reference)
   - https://www.gradio.app/guides/backend (EVENTS documentation)

2. **IDENTIFY all required props** that Gradio passes to components:
   - `value` - component's data
   - `loading_status` - if using StatusTracker
   - `gradio` - **CRITICAL**: provides i18n, autoscroll, dispatch()
   - Other props: elem_id, elem_classes, visible, etc.

3. **If using StatusTracker**, VERIFY what props it requires:
   - Check @gradio/statustracker npm package
   - Confirm `i18n` is REQUIRED (no default value)
   - Confirm `autoscroll` is expected

4. **Use Svelte 4 syntax** (`export let`) NOT Svelte 5 runes (`$props`, `$effect`)
   - ALL Gradio examples use Svelte 4
   - Svelte 5 runes are undocumented with Gradio components

5. **For Python backend**, check if EVENTS are needed:
   - Components that emit events need `EVENTS = [Events.change]`

### VERIFICATION before claiming "done":
- [ ] Compare Index.svelte line-by-line against PDF Component Example
- [ ] Confirm gradio prop is declared
- [ ] Confirm i18n is passed to StatusTracker
- [ ] Check browser console for JavaScript errors
- [ ] Test on fresh browser (not cached)
```

---

## Lessons Learned (Updated Post-Validation)

### 1. Official Documentation Is Not Optional

The agent assumed it knew Gradio patterns from general knowledge. It did NOT thoroughly read the official docs. **The `gradio` prop is clearly documented** in the Frontend Guide.

### 2. "Works Locally" ≠ "Works Correctly"

The component loaded locally because the browser cached state or errors were swallowed. A fresh test or HF Spaces deployment revealed the crash.

### 3. Using Components Requires Understanding Their Contracts

`StatusTracker` is a black box. The agent used it without checking:
- What props it requires
- What happens if `i18n` is undefined
- Whether it has default values

### 4. Spec Review Must Validate Against Official Examples

The spec was reviewed for:
- ✅ File structure
- ✅ Build process
- ✅ HF Spaces deployment
- ❌ **Component prop requirements** (MISSED)
- ❌ **StatusTracker requirements** (MISSED)
- ❌ **`.gitignore` patterns** (MISSED - templates were ignored!)

### 5. ~~Svelte 5 Runes Are Risky With Gradio~~ **REFUTED**

**Correction:** External validation proved Gradio 6 ships with Svelte 5.43.14 and supports runes. The issue was the missing `gradio` prop, not the syntax choice.

### 6. NEW: Check .gitignore Before Assuming Files Are Committed

The templates/ directory was ignored by `.gitignore`. Even though existing files were tracked, any rebuild would create new files that Git ignores. **Always verify .gitignore patterns when dealing with build artifacts.**

### 7. NEW: External Validation Is Critical for Complex Issues

Two independent external agents validated our findings and caught:
- The `.gitignore` issue we missed
- Refuted the Svelte 5 concern
- Confirmed the exact mechanism (i18n deref crash)

---

## Summary (Post External Validation)

**Root Cause #1:** The UI freeze is caused by StatusTracker crashing due to missing `i18n` prop. The `i18n` is provided by the `gradio` prop, which our component never declares. The compiled JS dereferences `e.i18n()` which throws a TypeError, blocking Svelte hydration.

**Root Cause #2:** The `.gitignore` file ignores `backend/**/templates/`, meaning any rebuilt component assets won't be committed. This is a deployment time bomb.

**Why it was missed:** The spec didn't thoroughly read official Gradio documentation OR check `.gitignore` patterns.

**The fix is straightforward (P0 only):**
1. Add `gradio: Gradio<{...}>` to Props interface in Index.svelte
2. Pass `gradio.i18n` and `gradio.autoscroll` to StatusTracker
3. Remove `backend/**/templates/` from `.gitignore`
4. Rebuild with `gradio cc build`
5. Commit the new templates

**NOT required (per external validation):**
- Converting to Svelte 4 syntax (Svelte 5 runes are fine)
- Adding EVENTS to Python backend (output components don't need it)

**For future custom components:** Always read the official Frontend Guide and PDF Component Example FIRST, verify your implementation matches, AND check `.gitignore` patterns for build artifacts.
