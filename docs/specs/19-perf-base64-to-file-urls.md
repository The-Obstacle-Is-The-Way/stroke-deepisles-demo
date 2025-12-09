# Issue #19: Replace Base64 Data URLs with File URLs for NiiVue Viewer

## Status: OPEN

**Date:** 2025-12-09
**Priority:** P3 (Performance optimization)
**GitHub Issue:** https://github.com/The-Obstacle-Is-The-Way/stroke-deepisles-demo/issues/19
**Related:** Bug #10, Bug #11 (both FIXED)

---

## TL;DR

Replace base64-encoded data URLs (~65MB payloads) with Gradio's file serving for
NiiVue volumes. The viewer works correctly now, but large payloads may cause
slow loading or memory issues.

---

## Problem

The NiiVue 3D viewer currently uses base64-encoded data URLs to pass NIfTI
volumes to the browser:

```python
# Current implementation in viewer.py
def nifti_to_data_url(nifti_path: Path) -> str:
    """Convert NIfTI file to base64 data URL."""
    data = nifti_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:application/octet-stream;base64,{b64}"
```

### Payload Size Analysis

| File | Raw Size | Base64 Size |
|------|----------|-------------|
| DWI | 30.1 MB | ~40 MB |
| ADC | 17.7 MB | ~24 MB |
| **Total** | ~48 MB | **~65 MB** |

### Potential Issues

1. **Browser memory pressure** - Large base64 strings in DOM
2. **Slow loading times** - 65MB transferred per segmentation
3. **Gradio payload limits** - May hit internal limits on large responses
4. **Mobile/low-bandwidth issues** - Poor UX on slower connections

---

## Proposed Solution

Use Gradio's built-in file serving instead of base64 data URLs.

### Option A: Use `gr.File` component (Recommended)

Gradio automatically serves files and provides URLs:

```python
from gradio import FileData

def nifti_to_file_url(nifti_path: Path) -> str:
    """Get Gradio file URL for NIfTI file."""
    file_data = FileData(path=str(nifti_path))
    return file_data.url  # Returns /file=... URL served by Gradio
```

### Option B: Use Gradio's file caching

```python
import gradio as gr

# Gradio caches files and provides URLs
cached_path = gr.utils.get_upload_folder() / nifti_path.name
shutil.copy(nifti_path, cached_path)
file_url = f"/file={cached_path}"
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/stroke_deepisles_demo/ui/viewer.py` | Replace `nifti_to_data_url()` with file URL function |
| `src/stroke_deepisles_demo/ui/app.py` | Update `run_segmentation()` to use file URLs |

---

## Implementation Steps

### Step 1: Research Gradio File Serving

Verify how Gradio serves files and what URL format NiiVue expects:

```python
# Test script
import gradio as gr
from gradio import FileData

file_data = FileData(path="/path/to/test.nii.gz")
print(f"URL: {file_data.url}")
print(f"Type: {type(file_data.url)}")
```

### Step 2: Update `nifti_to_data_url()` → `nifti_to_file_url()`

```python
# viewer.py
def nifti_to_file_url(nifti_path: Path) -> str:
    """Get Gradio-served file URL for NIfTI file.

    Args:
        nifti_path: Path to NIfTI file

    Returns:
        URL string that Gradio will serve (e.g., /file=...)
    """
    from gradio import FileData
    file_data = FileData(path=str(nifti_path))
    return file_data.url
```

### Step 3: Update `app.py` to Use File URLs

```python
# app.py - run_segmentation()
# Replace:
dwi_url = nifti_to_data_url(dwi_path)
mask_url = nifti_to_data_url(result.prediction_mask)

# With:
dwi_url = nifti_to_file_url(dwi_path)
mask_url = nifti_to_file_url(result.prediction_mask)
```

### Step 4: Test NiiVue with File URLs

Verify NiiVue can load from Gradio's file URLs:
- Check CORS headers
- Verify Content-Type header
- Test with different browsers

### Step 5: Cleanup

Remove or deprecate `nifti_to_data_url()` if no longer needed.

---

## Testing Checklist

- [ ] NiiVue loads DWI volume from file URL
- [ ] NiiVue loads prediction mask overlay from file URL
- [ ] No CORS errors in browser console
- [ ] Loading time improved (measure before/after)
- [ ] Memory usage reduced (check browser DevTools)
- [ ] Works on HF Spaces deployment
- [ ] All existing tests pass

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| CORS issues | Gradio should handle CORS for its own file serving |
| NiiVue URL format | Test that NiiVue accepts relative URLs |
| File cleanup | Gradio handles temp file cleanup automatically |
| Security | Gradio's file serving is sandboxed to allowed paths |

---

## Acceptance Criteria

1. NiiVue viewer loads volumes from file URLs (not base64)
2. No regression in viewer functionality
3. Measurable improvement in loading time or memory usage
4. All 130+ tests pass
5. Works on HF Spaces

---

## References

- [Gradio FileData API](https://www.gradio.app/docs/gradio/filedata)
- [Gradio File Serving](https://www.gradio.app/guides/file-access)
- [NiiVue Loading Volumes](https://niivue.github.io/niivue/features/loading.volumes.html)
- [Bug #10 - Secondary Issue 1](./10-bug-niivue-viewer-black-screen.md)
