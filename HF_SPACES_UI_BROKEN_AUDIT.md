# HF Spaces UI Completely Broken - Deep Audit

**Date:** 2025-12-10
**Branch:** `debug/hf-spaces-ui-completely-broken`
**Status:** P0 CRITICAL - App loads but UI is completely frozen

---

## Observed Symptoms (from screenshot)

1. **Two loading indicators showing simultaneously:**
   - "loading ..." (NiiVue's internal loading text, white text on black canvas)
   - "Loading..." (Gradio StatusTracker spinner, dark overlay)

2. **Nothing is clickable:**
   - Dropdown doesn't open
   - Buttons don't respond
   - Entire UI is frozen

3. **UI renders but is non-interactive:**
   - Layout appears correct
   - Components are visible
   - But no interaction possible

---

## Root Cause Analysis

### Issue 1: StatusTracker Missing Required `i18n` Prop

**Location:** `packages/niivueviewer/frontend/Index.svelte:119-124`

```svelte
{#if loading_status}
    <StatusTracker
        autoscroll={false}
        {...loading_status}
    />
{/if}
```

**Problem:** StatusTracker REQUIRES an `i18n` prop (I18nFormatter) with no default value:

```typescript
// From @gradio/statustracker/static/index.svelte:61
interface Props {
    i18n: I18nFormatter;  // REQUIRED - no default!
    eta?: number | null;
    // ...
}
```

**Impact:** Without `i18n`, StatusTracker throws a runtime error that may be blocking Svelte hydration.

### Issue 2: Svelte 5 Runes in Component, Unclear Gradio Compatibility

**Location:** `packages/niivueviewer/frontend/Index.svelte`

```svelte
let {
    value = null,
    // ...
}: Props = $props();  // Svelte 5 rune

$effect(() => {  // Svelte 5 rune
    if (value || value === null) {
        loadVolumes();
    }
});
```

**Problem:** The component uses Svelte 5 runes (`$props`, `$effect`), but there may be compatibility issues with how Gradio passes props to custom components.

**Evidence:** The compiled index.js imports from:
```javascript
import * as y from "../../../../../assets/svelte/svelte_internal_client.js";
```
This relative path expects Gradio's bundled Svelte. If there's any version mismatch, hydration fails.

### Issue 3: Loading Status Never Transitions to "complete"

**Location:** `packages/niivueviewer/backend/gradio_niivueviewer/niivueviewer.py`

**Problem:** The NiiVueViewer Python backend doesn't implement proper loading state management. Gradio components need to signal when they're done processing.

**Evidence:** The component class has no:
- `EVENTS` class attribute
- Loading state management
- Event dispatching

Compare to other Gradio components that properly manage loading states.

### Issue 4: NiiVue Canvas Shows "loading ..." Forever

**Location:** `packages/niivueviewer/frontend/Index.svelte:40-50`

```svelte
onMount(async () => {
    nv = new Niivue({...});
    await nv.attachToCanvas(canvas);
    await loadVolumes();
});
```

**Problem:** NiiVue initializes and shows "loading ..." while waiting for volumes. But `value` starts as `null`, so `loadVolumes()` just calls `nv.drawScene()` which keeps the "loading" text.

NiiVue's `drawLoadingText()` is called during initialization and stays until volumes are loaded.

### Issue 5: Dropdown Shows "Initializing dataset... please wait"

**Location:** `src/stroke_deepisles_demo/ui/components.py:27`

```python
return gr.Dropdown(
    choices=[],
    value=None,
    label="Select Case",
    info="Initializing dataset... please wait.",
    # ...
)
```

**Coupled with:** `src/stroke_deepisles_demo/ui/app.py:253`

```python
demo.load(initialize_case_selector, outputs=[case_selector])
```

**Problem:** `demo.load()` triggers AFTER Svelte hydration. If hydration is blocked (by Issues 1-2), the dropdown initialization never completes.

### Issue 6: Potential WebGL Context Loss

**Location:** `packages/niivueviewer/frontend/Index.svelte:40-49`

**Problem:** NiiVue creates a WebGL2 context during `onMount`. If:
1. The component mounts
2. StatusTracker throws an error
3. Svelte tries to unmount/remount
4. WebGL context gets lost

The canvas becomes unresponsive.

---

## Component Architecture Problems

### Python Backend (niivueviewer.py)

| Issue | Description | Impact |
|-------|-------------|--------|
| No EVENTS | Component doesn't define events like `change`, `input` | Gradio can't track state changes |
| No Streamable | Not marked as streamable component | May cause loading state issues |
| Simple data model | Just URLs, no loading state | Can't signal "done loading" |

### Svelte Frontend (Index.svelte)

| Issue | Description | Impact |
|-------|-------------|--------|
| Missing i18n | StatusTracker needs i18n prop | Runtime error |
| Svelte 5 runes | Modern syntax may have edge cases | Potential hydration issues |
| No error boundaries | JS errors propagate up | Entire UI breaks |
| Async onMount | loadVolumes() is async but errors not caught | Silent failures |

---

## Files Involved

| File | Lines | Issues |
|------|-------|--------|
| `packages/niivueviewer/frontend/Index.svelte` | 146 | StatusTracker i18n, Svelte 5, error handling |
| `packages/niivueviewer/backend/gradio_niivueviewer/niivueviewer.py` | 78 | Missing events, loading state |
| `src/stroke_deepisles_demo/ui/components.py` | 93 | NiiVueViewer integration |
| `src/stroke_deepisles_demo/ui/app.py` | 290 | demo.load timing |

---

## Hypotheses to Test

### Hypothesis A: StatusTracker i18n Error (HIGH CONFIDENCE)
**Test:** Remove StatusTracker from Index.svelte entirely
**Expected:** UI becomes interactive (even if loading indicator is missing)

### Hypothesis B: Svelte Hydration Blocked (MEDIUM CONFIDENCE)
**Test:** Check browser console for Svelte errors
**Expected:** See "Cannot read property of undefined" or similar

### Hypothesis C: demo.load() Timing Issue (MEDIUM CONFIDENCE)
**Test:** Remove demo.load() call, hardcode dropdown choices
**Expected:** Dropdown works immediately

### Hypothesis D: WebGL Context Issue (LOW CONFIDENCE)
**Test:** Replace NiiVue canvas with static div
**Expected:** UI works, only viewer broken

---

## Recommended Fixes (Priority Order)

### Fix 1: Remove StatusTracker (IMMEDIATE)

```svelte
<!-- REMOVE THIS BLOCK -->
{#if loading_status}
    <StatusTracker
        autoscroll={false}
        {...loading_status}
    />
{/if}
```

NiiVue has its own loading indicator. We don't need Gradio's.

### Fix 2: Add Error Boundary in onMount

```svelte
onMount(async () => {
    try {
        nv = new Niivue({...});
        await nv.attachToCanvas(canvas);
        await loadVolumes();
    } catch (error) {
        console.error('[NiiVue] Initialization failed:', error);
        // Show fallback UI
    }
});
```

### Fix 3: Handle Empty Value State

```svelte
async function loadVolumes() {
    if (!nv) return;

    // Clear existing volumes
    while (nv.volumes.length > 0) {
        nv.removeVolume(nv.volumes[0]);
    }

    if (!value || (!value.background_url && !value.overlay_url)) {
        // Show placeholder instead of "loading ..."
        nv.drawScene();
        return;
    }
    // ...
}
```

### Fix 4: Remove Loading Status Prop

If we don't need StatusTracker, remove the prop entirely:

```svelte
interface Props {
    value?: { background_url: string | null; overlay_url: string | null } | null;
    label?: string;
    show_label?: boolean;
    // loading_status?: LoadingStatus;  // REMOVE
    // ...
}
```

---

## Questions for Further Investigation

1. **Why does Example.svelte use Svelte 4 syntax (`export let`) while Index.svelte uses Svelte 5 (`$props`)?**
   - Are they supposed to match?
   - Was this an incomplete migration?

2. **How do other Gradio custom components handle StatusTracker?**
   - Do they pass `i18n`?
   - Or do they skip StatusTracker entirely?

3. **What exactly does Gradio pass as `loading_status`?**
   - Does it include `i18n`?
   - Or is it expected to be provided separately?

4. **Is the component even receiving props correctly?**
   - Add console.log in onMount to verify

---

## Browser Console Commands to Debug

```javascript
// Check if Gradio app is properly initialized
console.log(window.gradio_config);

// Check for Svelte errors
// Look for errors containing "props", "undefined", "i18n"

// Check NiiVue state
// Find the canvas element and check its WebGL context
const canvas = document.querySelector('canvas');
const gl = canvas?.getContext('webgl2');
console.log('WebGL2 context:', gl ? 'available' : 'LOST');

// Check if StatusTracker is blocking
document.querySelectorAll('[data-testid="status-tracker"]').forEach(el => {
    console.log('StatusTracker:', el.className);
});
```

---

## Next Steps

1. [ ] Test Hypothesis A: Remove StatusTracker
2. [ ] Check browser console for JS errors
3. [ ] Add diagnostic logging to component
4. [ ] Compare with working Gradio custom components
5. [ ] Consider simplifying to just canvas (no StatusTracker, no loading_status)

---

## References

- [Gradio Custom Components Guide](https://www.gradio.app/guides/custom-components-in-five-minutes)
- [Gradio Issue #11881: Upgrade to Svelte 5](https://github.com/gradio-app/gradio/issues/11881)
- [StatusTracker Source](packages/niivueviewer/frontend/node_modules/@gradio/statustracker/static/index.svelte)
- [NiiVue Documentation](https://niivue.com/docs/)
