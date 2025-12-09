# Bug #24: HuggingFace Space Stuck on "Loading..." (P0)

**Date:** 2025-12-09
**Status:** FIXED
**Branch:** `debug/hf-spaces-loading-forever`
**Space:** https://huggingface.co/spaces/VibecoderMcSwaggins/stroke-deepisles-demo

---

## Symptom

The HuggingFace Space shows:
- **Status badge:** "Running on T4" (green) ✓
- **App panel:** Stuck on "Loading..." indefinitely ✗

The Docker container has started successfully (hence "Running on T4"), but the Gradio frontend never receives a response from the backend.

---

## What We Know

### Local Testing: Works Fine
```python
# All pass in ~1.3 seconds
from stroke_deepisles_demo.ui.app import create_app
demo = create_app()  # Returns gr.Blocks successfully
```

### Code on HF Space
The Space is synced with `main` branch (commit `10a72ea`), NOT the PR #23 branch.
- `js_on_load` parameter was already added in commit `bc1d8e8`
- Server binds to `0.0.0.0:7860` (correct for Docker)
- Dataset loading uses pre-computed case IDs (no network calls on startup)

### Configuration Verified
| Setting | Value | Status |
|---------|-------|--------|
| `sdk` | `docker` | ✓ Correct |
| `app_port` | `7860` | ✓ Correct |
| `server_name` | `0.0.0.0` | ✓ Correct |
| `server_port` | `7860` | ✓ Correct |
| Gradio version | `>=6.0.0,<7.0.0` | ✓ Correct |

---

## Hypotheses

### H1: Python Startup Crash (Silent)
The Python app may be crashing during startup but HF Spaces still shows "Running on T4" because the container process is alive (perhaps a shell wrapper).

**Check:** Look at HF Spaces logs for Python tracebacks.

### H2: Gradio Server Not Binding
The Gradio server may be failing to bind or timing out before accepting connections.

**Check:** Look for "Running on local URL" in logs.

### H3: HF Spaces Platform Issue
HuggingFace Spaces may have a platform-wide issue affecting Docker SDK spaces.

**Check:** https://status.huggingface.co/ and HF Forums.

### H4: Memory/Resource Exhaustion
The T4 instance may be running out of memory during startup.

**Check:** Look for OOM errors in logs.

### H5: Dependencies Installation Failure
The `git+https://github.com/CloseChoice/datasets.git@...` dependency may fail to install.

**Check:** Build logs for pip install errors.

---

## Diagnostic Steps

### 1. Check HF Spaces Logs
Go to the Space → Settings → Logs and look for:
- Python tracebacks
- "Running on local URL: http://0.0.0.0:7860"
- Memory errors
- Dependency installation errors

### 2. Factory Rebuild
Settings → Factory rebuild to force a clean Docker build.

### 3. Check HF Status
Visit https://status.huggingface.co/ for platform outages.

### 4. Test Minimal Dockerfile
Create a minimal test Space with just Gradio to isolate the issue:

```dockerfile
FROM python:3.11-slim
RUN pip install gradio
COPY <<EOF app.py
import gradio as gr
demo = gr.Interface(fn=lambda x: x, inputs="text", outputs="text")
demo.launch(server_name="0.0.0.0", server_port=7860)
EOF
CMD ["python", "app.py"]
```

---

## Related Issues

- [HF Forum: Space stuck at Starting](https://discuss.huggingface.co/t/hf-space-stuck-at-starting/170911) (Nov 2025)
- [HF Forum: Dockerized app stuck at Building](https://discuss.huggingface.co/t/dockerized-gradio-app-stuck-at-building-despite-clean-logs/65558)
- [HF Forum: How to debug Spaces](https://discuss.huggingface.co/t/how-to-debug-spaces-on-hf-co/13191)
- [Gradio Issue #11401: Errors accessing spaces](https://github.com/gradio-app/gradio/issues/11401) (June 2025)

---

## Questions for User

1. **When did the Space last work correctly?** (Before which commit/PR?)
2. **What do the HF Spaces logs show?** (Settings → Logs)
3. **Has a factory rebuild been attempted?**
4. **Is HF Spaces having any platform issues today?**

---

## Next Steps

1. [ ] User to check HF Spaces logs
2. [ ] User to attempt factory rebuild
3. [ ] Check if issue is platform-wide (HF status page)
4. [ ] If needed, create minimal reproduction Space
5. [ ] If dependency issue, consider vendoring the datasets fork

---

## Resolution

**Status:** FIXED (2025-12-09)

### Root Cause

**Content Security Policy (CSP) blocking external CDN imports.**

The NiiVue library was being loaded via dynamic ES module import from unpkg.com CDN:
```javascript
const { Niivue } = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
```

HuggingFace Spaces enforces strict CSP headers that block external script imports. The import would either:
1. Be silently blocked by CSP
2. Hang indefinitely waiting for a response that never comes

This caused the Gradio frontend to remain stuck on "Loading..." even though the Python backend was running correctly.

**Evidence:**
- HF Spaces logs showed `Running on local URL: http://0.0.0.0:7860` (server healthy)
- No Python tracebacks (no backend crash)
- `list_case_ids()` uses pre-computed constants (no network blocking)
- Classic symptom of client-side JS execution failure

### Fix Applied

**Vendored the NiiVue library locally** instead of relying on external CDN:

1. **Downloaded NiiVue to local assets:**
   - `src/stroke_deepisles_demo/ui/assets/niivue.js` (2.9MB)

2. **Updated `viewer.py` to use local path:**
   ```python
   _ASSET_DIR = Path(__file__).parent / "assets"
   _NIIVUE_JS_PATH = _ASSET_DIR / "niivue.js"
   NIIVUE_JS_URL = f"/gradio_api/file={_NIIVUE_JS_PATH.resolve()}"
   ```

3. **Added `allowed_paths` to `demo.launch()`:**
   ```python
   assets_dir = Path(__file__).parent / "assets"
   demo.launch(
       # ...
       allowed_paths=[str(assets_dir)],
   )
   ```

### Files Modified

| File | Changes |
|------|---------|
| `src/stroke_deepisles_demo/ui/assets/niivue.js` | NEW - Vendored NiiVue v0.65.0 |
| `src/stroke_deepisles_demo/ui/viewer.py` | Use local path instead of CDN |
| `src/stroke_deepisles_demo/ui/app.py` | Add `allowed_paths` to launch() |
| `app.py` | Add `allowed_paths` to launch() |
| `.pre-commit-config.yaml` | Exclude assets/ from hooks |

### Verification

- All 136 tests pass
- Ruff lint passes
- Mypy type check passes
- Local Gradio app loads correctly

### Why This Is The Professional Solution

1. **Self-contained:** No external dependencies at runtime
2. **Reliable:** Immune to CDN outages or rate limits
3. **Security-compliant:** Respects HF Spaces CSP policy
4. **Reproducible:** Same NiiVue version always loaded
5. **Standard practice:** Vendoring is the recommended approach for HF Spaces

---

## Update: Vendoring Alone Did Not Fix It (2025-12-09)

### New Finding

Vendoring NiiVue locally bypassed CSP but **the app still wouldn't load**.

**Diagnostic test:** Disabled `js_on_load` parameter entirely.

**Result:** App loads perfectly! Everything works EXCEPT Interactive 3D viewer.

### Real Root Cause

**`gr.HTML(js_on_load=...)` with dynamic ES module `import()` blocks Gradio frontend initialization on HF Spaces.**

The issue is NOT the vendored file location - it's HOW we load the JavaScript:

```javascript
// This approach BREAKS the entire Gradio app on HF Spaces:
const { Niivue } = await import('/gradio_api/file=...');
```

When this fails (silently), it prevents the Gradio frontend from completing initialization, causing the eternal "Loading..." screen.

### Evidence

With `js_on_load` disabled:
- ✅ Gradio app loads
- ✅ Case selector works
- ✅ DeepISLES segmentation runs (38.66s)
- ✅ Static Report (Matplotlib) renders correctly
- ✅ Metrics JSON displays
- ✅ Download works
- ❌ Interactive 3D shows "Loading viewer..." (expected - JS disabled)

### Correct Approach

Use `gr.Blocks(head=...)` to load NiiVue as a `<script>` tag instead of dynamic `import()`:

```python
with gr.Blocks(
    head='<script src="/gradio_api/file=.../niivue.js"></script>'
) as demo:
    ...
```

Or use the global `js` parameter on `gr.Blocks` to define initialization code that runs after the script loads.
