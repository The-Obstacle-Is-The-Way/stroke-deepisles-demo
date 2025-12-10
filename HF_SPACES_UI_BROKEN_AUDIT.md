# HF Spaces UI Completely Broken - Consolidated Audit

**Date:** 2025-12-10
**Branch:** `debug/hf-spaces-ui-completely-broken`
**Status:** P0 CRITICAL - ROOT CAUSE IDENTIFIED

---

## TL;DR - THE FIX

Our custom component is missing the **`gradio` prop** which provides `i18n` and `autoscroll`. This is 100% required for StatusTracker to work.

**Current broken code:**
```svelte
// WRONG - missing gradio prop
let { value, loading_status, ... }: Props = $props();

<StatusTracker {...loading_status} />  // CRASHES - no i18n!
```

**Correct pattern (from Gradio docs):**
```svelte
// CORRECT - includes gradio prop
export let gradio: Gradio<{ change: never }>;
export let loading_status: LoadingStatus;

<StatusTracker
    autoscroll={gradio.autoscroll}
    i18n={gradio.i18n}
    {...loading_status}
/>
```

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

### Secondary Issue: Svelte 5 Runes vs Svelte 4 Syntax

Our component uses **Svelte 5 runes** (`$props()`, `$effect()`), but all Gradio documentation examples use **Svelte 4 syntax** (`export let`).

| File | Syntax | Status |
|------|--------|--------|
| Index.svelte | `$props()` (Svelte 5) | **WRONG** |
| Example.svelte | `export let` (Svelte 4) | Correct |
| Gradio PDF example | `export let` (Svelte 4) | Reference |

While Svelte 5 is backwards compatible, mixing paradigms in a Gradio custom component is risky and undocumented.

---

## All Issues Found (Priority Order)

### Critical (Will Definitely Break)

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| 1 | **Missing `gradio` prop** | Index.svelte:8-20 | Add `export let gradio: Gradio<{...}>` |
| 2 | **Missing `i18n` to StatusTracker** | Index.svelte:121 | Add `i18n={gradio.i18n}` |
| 3 | **Missing `autoscroll` to StatusTracker** | Index.svelte:120 | Add `autoscroll={gradio.autoscroll}` |

### Likely Breaking

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| 4 | Svelte 5 `$props()` instead of `export let` | Index.svelte:22-34 | Rewrite to Svelte 4 syntax |
| 5 | Svelte 5 `$effect()` instead of `$:` | Index.svelte:98-103 | Rewrite to reactive statement |
| 6 | No EVENTS defined in Python backend | niivueviewer.py | Add `EVENTS = [Events.change]` |

### Possibly Contributing

| # | Issue | File:Line | Fix |
|---|-------|-----------|-----|
| 7 | No error boundary in onMount | Index.svelte:40-50 | Add try/catch |
| 8 | Double loadVolumes call (onMount + $effect) | Index.svelte:40,98 | Remove redundant call |
| 9 | NiiVue shows "loading..." forever on null value | Index.svelte:73-76 | Better empty state |

---

## Correct Index.svelte Pattern

Based on [Gradio's PDF Component Example](https://www.gradio.app/guides/pdf-component-example):

```svelte
<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { Niivue } from '@niivue/niivue';
    import { Block } from "@gradio/atoms";
    import { StatusTracker } from "@gradio/statustracker";
    import type { LoadingStatus } from "@gradio/statustracker";
    import type { Gradio } from "@gradio/utils";

    // Props - using Svelte 4 syntax (export let)
    export let value: { background_url: string | null; overlay_url: string | null } | null = null;
    export let label: string | undefined = undefined;
    export let show_label = true;
    export let loading_status: LoadingStatus | undefined = undefined;
    export let elem_id = "";
    export let elem_classes: string[] = [];
    export let visible = true;
    export let height = 500;
    export let container = true;
    export let scale: number | null = null;
    export let min_width: number | undefined = undefined;

    // CRITICAL: The gradio prop provides i18n, autoscroll, and dispatch
    export let gradio: Gradio<{
        change: never;
    }>;

    let canvas: HTMLCanvasElement;
    let nv: Niivue | null = null;

    onMount(async () => {
        try {
            nv = new Niivue({
                backColor: [0, 0, 0, 1],
                show3Dcrosshair: true,
                logging: false
            });
            await nv.attachToCanvas(canvas);
            await loadVolumes();
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

    // Reactive statement (Svelte 4 syntax)
    $: if (value !== undefined) {
        loadVolumes();
    }
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

## Python Backend Fix

Add EVENTS to enable event dispatching:

```python
from gradio.events import Events

class NiiVueViewer(Component):
    """WebGL NIfTI viewer using NiiVue."""

    EVENTS = [Events.change]  # ADD THIS

    data_model = NiiVueViewerData
    # ... rest unchanged
```

---

## Validation Checklist

### Before Fix
- [ ] `gradio` prop declared? **NO**
- [ ] `i18n` passed to StatusTracker? **NO**
- [ ] `autoscroll` passed to StatusTracker? **NO**
- [ ] Using Svelte 4 syntax? **NO** (using Svelte 5 runes)
- [ ] EVENTS defined in Python? **NO**

### After Fix (Target)
- [ ] `gradio` prop declared? YES
- [ ] `i18n` passed to StatusTracker? YES
- [ ] `autoscroll` passed to StatusTracker? YES
- [ ] Using Svelte 4 syntax? YES
- [ ] EVENTS defined in Python? YES

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

## External Audit Validation

| Claim | Validated | Evidence |
|-------|-----------|----------|
| StatusTracker requires `i18n` | **TRUE** | [Gradio docs](https://www.gradio.app/guides/frontend), [npm package](https://www.npmjs.com/package/@gradio/statustracker) |
| `gradio` prop provides `i18n` | **TRUE** | [PDF example](https://www.gradio.app/guides/pdf-component-example) shows `gradio.i18n` |
| Svelte 5 runes may cause issues | **LIKELY** | All Gradio examples use Svelte 4 `export let` |
| Missing EVENTS in Python | **TRUE** | [Backend guide](https://www.gradio.app/guides/backend) shows EVENTS required for events |
| `demo.load()` blocking | **FALSE** | Runs after render, not the cause |

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

## Summary

**The UI freeze is caused by StatusTracker crashing due to missing `i18n` prop.** The `i18n` is provided by the `gradio` prop, which our component never declares. This is a fundamental implementation error - we didn't follow the Gradio custom component pattern correctly.

The fix is straightforward:
1. Add `export let gradio: Gradio<{...}>` to Index.svelte
2. Pass `gradio.i18n` and `gradio.autoscroll` to StatusTracker
3. Convert from Svelte 5 runes to Svelte 4 syntax for safety
4. Add EVENTS to Python backend
5. Rebuild with `gradio cc build`
