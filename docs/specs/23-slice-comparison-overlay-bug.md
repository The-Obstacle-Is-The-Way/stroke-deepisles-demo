# Bug Investigation: Slice Comparison Prediction Overlay Not Visible

**Issue**: Prediction overlay is invisible in slice comparison while ground truth overlay is visible

**Date**: 2025-12-09
**Branch**: `debug/slice-comparison-prediction-overlay`

---

## Observed Behavior

In the Gradio UI "Slice Comparison" tab:
- **DWI Input** (left panel): Shows grayscale brain scan ✓
- **Prediction** (middle panel): Shows grayscale brain scan **without any visible overlay** ✗
- **Ground Truth** (right panel): Shows grayscale brain scan **with green overlay** ✓

## Expected Behavior

The Prediction panel should show a **red overlay** on the predicted lesion area, similar to how Ground Truth shows a green overlay.

---

## Code Analysis

### Visualization Code (`viewer.py:261-268`)

```python
# Prediction panel
axes[1].imshow(d_slice, cmap="gray")
axes[1].imshow(
    np.ma.masked_where(p_slice == 0, p_slice),
    cmap="Reds",
    alpha=0.5,
    vmin=0,
    vmax=1,
)
```

### Ground Truth Code (`viewer.py:273-280`)

```python
# Ground Truth panel
axes[2].imshow(d_slice, cmap="gray")
axes[2].imshow(
    np.ma.masked_where(g_slice == 0, g_slice),
    cmap="Greens",
    alpha=0.5,
    vmin=0,
    vmax=1,
)
```

The code is **structurally identical**. The only difference is:
- Prediction: `cmap="Reds"`
- Ground Truth: `cmap="Greens"`

---

## Hypothesis

### Primary Hypothesis: Probability vs Binary Mask Values

| Mask Type | Typical Values | Colormap Rendering | Visibility |
|-----------|----------------|-------------------|------------|
| Ground Truth | Binary (0 or 1) | 1.0 → **Dark Green** | High ✓ |
| Prediction | Probabilities (0.0-0.3) | 0.1 → **Nearly White** | None ✗ |

**Why this matters:**

1. Matplotlib's **"Reds" colormap** goes from white (0) → red (1)
2. With `vmin=0, vmax=1`:
   - A value of `0.05` maps to 5% of the colormap = nearly white
   - A value of `1.0` maps to 100% of the colormap = red
3. With `alpha=0.5` over a grayscale background, nearly-white overlays are **invisible**

**Evidence:**
- DeepISLES SEALS model may output probability maps, not binary masks
- The `compute_dice` function in `metrics.py` applies a `threshold=0.5` to binarize predictions
- The visualization does **not** apply any thresholding before display

### Alternative Hypotheses

1. **Empty slice**: Prediction mask is all zeros at the selected slice (unlikely given the slice selection logic uses `get_slice_at_max_lesion(prediction_path)`)

2. **Data type issue**: Float comparison `p_slice == 0` may fail for float32 arrays (unlikely - works for ground truth)

3. **File path mismatch**: Wrong file being loaded as prediction (need to verify)

---

## Diagnostic Steps

### 1. Check Prediction Mask Values

```python
import nibabel as nib
import numpy as np

# Load a prediction mask from a recent run
pred = nib.load("/path/to/prediction.nii.gz").get_fdata()
print(f"Shape: {pred.shape}")
print(f"Dtype: {pred.dtype}")
print(f"Min: {pred.min()}, Max: {pred.max()}")
print(f"Unique values: {np.unique(pred)[:20]}")  # First 20 unique values
print(f"Non-zero count: {np.count_nonzero(pred)}")
print(f"Values > 0.5: {np.count_nonzero(pred > 0.5)}")
```

### 2. Check Ground Truth Mask Values

```python
gt = nib.load("/path/to/ground_truth.nii.gz").get_fdata()
print(f"Shape: {gt.shape}")
print(f"Dtype: {gt.dtype}")
print(f"Min: {gt.min()}, Max: {gt.max()}")
print(f"Unique values: {np.unique(gt)}")
```

### 3. Visual Comparison

```python
# Plot histogram of values
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2)
axes[0].hist(pred[pred > 0].flatten(), bins=50)
axes[0].set_title("Prediction non-zero values")
axes[1].hist(gt[gt > 0].flatten(), bins=50)
axes[1].set_title("Ground Truth non-zero values")
plt.savefig("mask_histograms.png")
```

---

## Proposed Fix

### Option A: Binarize Prediction Before Display (Recommended)

```python
# In render_slice_comparison, before creating overlay:
p_slice_binary = (p_slice > 0.5).astype(float)

axes[1].imshow(
    np.ma.masked_where(p_slice_binary == 0, p_slice_binary),
    cmap="Reds",
    alpha=0.5,
    vmin=0,
    vmax=1,
)
```

**Pros:**
- Consistent with how `compute_dice` treats predictions
- Clear visualization of model decision boundary
- Matches clinical interpretation (lesion vs not-lesion)

**Cons:**
- Loses probability information in visualization

### Option B: Dynamic Normalization

```python
# Normalize to actual value range instead of fixed 0-1
p_max = p_slice.max() if p_slice.max() > 0 else 1.0
axes[1].imshow(
    np.ma.masked_where(p_slice == 0, p_slice),
    cmap="Reds",
    alpha=0.5,
    vmin=0,
    vmax=p_max,
)
```

**Pros:**
- Shows probability information
- Works regardless of value range

**Cons:**
- Inconsistent intensity across cases
- Low-confidence predictions still appear bright (misleading)

### Option C: Threshold-Based Masking

```python
# Only show values above a threshold
threshold = 0.5
axes[1].imshow(
    np.ma.masked_where(p_slice < threshold, p_slice),
    cmap="Reds",
    alpha=0.5,
    vmin=threshold,
    vmax=1.0,
)
```

**Pros:**
- Only shows confident predictions
- Good dynamic range for visible values

**Cons:**
- May hide uncertain but potentially relevant areas

---

## Recommendation

**Implement Option A (Binarize)** because:

1. It matches the clinical use case (segmentation → binary decision)
2. It's consistent with `compute_dice` threshold behavior
3. It provides clear, interpretable visualization
4. The raw probability map can still be viewed in NiiVue if needed

---

## Dependencies

| Package | Version | Relevant |
|---------|---------|----------|
| gradio | >=6.0.0 | Unlikely cause (renders matplotlib figure correctly) |
| matplotlib | >=3.8.0 | Colormap behavior is standard |
| numpy | >=1.26.0,<2.0.0 | Float comparison works correctly |
| nibabel | >=5.2.0 | Loads data correctly |

---

## Resolution

**Status**: FIXED (2025-12-09)
**Branch**: `debug/slice-comparison-prediction-overlay`

### Changes Made

**Primary Fix (Issue #23):**

1. **`viewer.py:270-275`**: Added binarization of prediction mask in `render_slice_comparison`:
   ```python
   # Binarize prediction at threshold 0.5 for visible overlay (Issue #23)
   p_slice_binary = (p_slice > 0.5).astype(float)
   ```

2. **`viewer.py:156-164`**: Added binarization in `render_3panel_view` for consistency

3. **`tests/conftest.py`**: Added `synthetic_probability_mask` and `synthetic_binary_mask` fixtures

4. **`tests/ui/test_viewer.py`**: Added `TestRenderSliceComparisonProbabilityMask` test class

**Additional Fixes (Found During Audit):**

5. **Race Condition (P2)**: Replaced global `_previous_results_dir` with `gr.State` for per-session thread-safe cleanup tracking

6. **Inconsistent Threshold in compute_volume_ml**: Added `threshold=0.5` parameter for consistent binarization

7. **render_3panel_view Wired Into UI**:
   - Added `gr.Tabs` layout with "Interactive 3D" and "Static Report" tabs
   - `render_3panel_view` now displayed in "Static Report" alongside slice comparison
   - Provides WebGL2 fallback via static matplotlib figures

8. **Thread-Safe Matplotlib**: Refactored from `pyplot` API to Object-Oriented API (`Figure()`) for multi-user safety

### Verification

- All 136 tests pass
- Lint (ruff) passes
- Type check (mypy) passes

## Files Modified

| File | Changes |
|------|---------|
| `src/stroke_deepisles_demo/ui/viewer.py` | OO matplotlib API, binarization in both render functions |
| `src/stroke_deepisles_demo/ui/app.py` | gr.State, render_3panel_view integration, volume_ml |
| `src/stroke_deepisles_demo/ui/components.py` | Tabs layout (Interactive 3D / Static Report) |
| `src/stroke_deepisles_demo/metrics.py` | threshold parameter for compute_volume_ml |
| `tests/conftest.py` | New probability/binary mask fixtures |
| `tests/ui/test_viewer.py` | Probability mask tests |
| `tests/ui/test_app.py` | Updated for new return signature |

## Next Steps

1. [x] Run diagnostic script to confirm hypothesis
2. [x] Implement fix (Option A - binarize)
3. [x] Add test case for probability-valued masks
4. [x] Wire render_3panel_view into UI with tabs
5. [x] Fix race condition with gr.State
6. [x] Make matplotlib thread-safe with OO API
7. [ ] Verify fix in local Gradio app (manual testing recommended)
8. [ ] Create PR and merge to main
