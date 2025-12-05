# spec: hugging face spaces + gradio deployment

> **Version**: December 2025
> **Status**: APPROVED - Ready for Implementation
> **Last Updated**: 2025-12-05
> **Verified**: Cold start claims, pause/restart behavior, ZeroGPU limitations

## important: gradio 6 is now available

As of December 2025, **Gradio 6.0.2** is the latest stable release. Our `pyproject.toml` currently specifies `gradio>=5.0.0`, which will install Gradio 6.x.

**Key breaking changes affecting our codebase:**

| Change | Impact | Our Code |
|--------|--------|----------|
| `theme`, `css`, `js` moved from `Blocks()` to `launch()` | HIGH | `app.py:111` uses `gr.Blocks()`, `app.py:170` passes theme to `launch()` - **OK** |
| `gr.HTML` padding default `True` → `False` | LOW | No visual impact expected |
| Chatbot tuple format removed | NONE | We don't use Chatbot |
| `show_api` → `footer_links` | LOW | We don't customize this |

**Recommendation**: Pin to `gradio>=6.0.0,<7.0.0` for stability, or test with latest and update as needed.

**Migration guide**: [Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)

---

## purpose

This spec documents the requirements, constraints, and best practices for deploying the `stroke-deepisles-demo` Gradio application to Hugging Face Spaces. It identifies potential friction points between our current implementation and HF Spaces constraints, providing concrete guidance before deployment.

## executive summary

### critical friction points identified

| Issue | Severity | Current State | Fix Required |
|-------|----------|---------------|--------------|
| **NVIDIA GPU required** | HIGH | DeepISLES needs CUDA | Use Docker SDK + GPU on HF Spaces |
| **JavaScript in `gr.HTML`** | HIGH | `<script type="module">` in viewer.py | May not execute; needs `js=` param pattern |
| **Git dependency in pyproject.toml** | MEDIUM | `datasets @ git+https://...` | Needs `requirements.txt` with git URL |
| **Large NIfTI files as base64** | MEDIUM | Full file loaded to memory | Should be fine with GPU tier RAM |
| **NiiVue version** | LOW | Currently 0.57.0 in viewer.py | Update to **0.65.0** (latest) |

### deployment strategy

> **Important**: DeepISLES requires NVIDIA GPU with CUDA. There is no CPU-only or Apple Silicon option. "Demo mode" with pre-computed results was rejected as it defeats the purpose of a real inference demo.

### Primary: Local NVIDIA GPU
- Develop and test locally with your NVIDIA GPU
- Free, unlimited, real inference
- Works on Windows/Linux with NVIDIA GPU (GTX 1080+, RTX series)

### Showcase: HF Spaces Docker SDK + GPU (On-Demand)
- Use `sdk: docker` with GPU hardware
- **Spin up** when demoing, **pause** when done
- Cost: ~$0.20-$0.40 per 30-60 min demo session
- Billing stops when paused ($0 while inactive)

---

## critical: cold start reality

> ⚠️ **OPERATIONAL MANDATE**: Always run `api.restart_space()` **20-30 minutes** before a scheduled demo. Verify the Space is "Running" before sharing your screen.

### verified cold start times (december 2025)

| Phase | Time | Source |
|-------|------|--------|
| HF Infrastructure boot | ~2 minutes | [HF Forums](https://discuss.huggingface.co/t/slow-space-cold-boot/72154) |
| Docker image provision | 5-20 minutes | Large images (CUDA + nnU-Net ~15-20GB) |
| Application startup | 1-5 minutes | Gradio + model loading |
| **Total (best case)** | **8-12 minutes** | Normal conditions |
| **Total (worst case)** | **30-60+ minutes** | Resource contention, Feb 2025 T4 issues |

**Sources**: [T4 startup 45+ min issue (Feb 2025)](https://discuss.huggingface.co/t/staring-up-t4-instances-is-taking-45-minutes/139567), [Cold boot discussion](https://discuss.huggingface.co/t/slow-space-cold-boot/72154)

### why cold start is unavoidable

From HF Staff (forum moderator):
> "avoiding a cold start here is not possible"

The ~2-minute infrastructure delay is inherent to HF Spaces architecture. Docker GPU Spaces add additional time for image provisioning and GPU allocation.

### deployment risks (edge cases)

| Risk | Frequency | Mitigation |
|------|-----------|------------|
| Space stuck in "Starting" | Rare | Factory rebuild, contact HF support |
| Space stuck in "Paused" | Rare | Wait + retry, contact HF support |
| Build timeout (30-45 min limit) | Possible | Optimize Dockerfile, cache layers |
| GPU unavailable (resource contention) | Rare | Try again later, different hardware tier |

**Sources**: [Space stuck at Starting (Nov 2025)](https://discuss.huggingface.co/t/hf-space-stuck-at-starting/170911), [Space stuck in Paused (Oct 2025)](https://discuss.huggingface.co/t/space-stuck-in-paused/169467)

### pre-demo warm-up procedure

```bash
# 20-30 minutes before your demo:

# 1. Restart the Space
python -c "
from huggingface_hub import HfApi
api = HfApi()
api.restart_space('YOUR_USERNAME/stroke-deepisles-demo')
print('Space restart initiated...')
"

# 2. Monitor status (check every 2 min)
python -c "
from huggingface_hub import HfApi
api = HfApi()
info = api.space_info('YOUR_USERNAME/stroke-deepisles-demo')
print(f'Status: {info.runtime.stage}')  # Should be 'RUNNING'
"

# 3. Only proceed when status = RUNNING
```

### contingency plan if cold start fails

1. **Space stuck in "Starting" > 30 min**:
   - Try "Factory rebuild" from Space Settings
   - If still stuck, contact HF support via [Discord](https://discord.gg/hugging-face-879548962464493619)

2. **Demo starts before Space is ready**:
   - Show local demo on your NVIDIA GPU machine instead
   - "Let me show you on my development machine while the cloud version warms up"

3. **GPU unavailable error**:
   - Try `a10g-small` instead of `t4-small` (different GPU pool)
   - Wait 15 minutes and retry

---

## zerogpu: why it doesn't work for us

ZeroGPU offers free, dynamic GPU allocation on H200 GPUs. However:

| Requirement | ZeroGPU | Our Need |
|-------------|---------|----------|
| SDK Support | Gradio SDK only | Docker SDK (for DeepISLES container) |
| Docker containers | ❌ NOT supported | ✅ Required |
| Custom CUDA environment | ❌ NOT supported | ✅ Required (nnU-Net) |

**Source**: [ZeroGPU Documentation](https://huggingface.co/docs/hub/en/spaces-zerogpu), [Community request for Docker support](https://huggingface.co/spaces/zero-gpu-explorers/README/discussions/27)

**Verdict**: ZeroGPU is incompatible with DeepISLES. We must use Docker SDK + paid GPU hardware.

---

## hugging face spaces constraints

### sdk options

| SDK | Use Case | Docker Access | GPU Support |
|-----|----------|---------------|-------------|
| `gradio` | Standard Gradio apps | **NO** | Via hardware upgrade |
| `docker` | Custom containers | **YES** | Via hardware upgrade |
| `static` | HTML/JS only | **NO** | N/A |

**Key insight**: The Gradio SDK **cannot run Docker containers**. Our pipeline requires the DeepISLES Docker image, creating a fundamental incompatibility.

### hardware tiers

| Tier | vCPU | RAM | Cost | GPU |
|------|------|-----|------|-----|
| cpu-basic (free) | 2 | 16GB | $0 | None |
| cpu-upgrade | 8 | 32GB | $0.03/hr | None |
| t4-small | 4 | 15GB | $0.40/hr | T4 (16GB) |
| t4-medium | 8 | 30GB | $0.60/hr | T4 (16GB) |
| a10g-small | 4 | 15GB | $1.05/hr | A10G (24GB) |
| a10g-large | 12 | 46GB | $3.15/hr | A10G (24GB) |

**Source**: [Hugging Face Spaces GPU Upgrades](https://huggingface.co/docs/hub/spaces)

### storage limits

| Type | Limit | Behavior |
|------|-------|----------|
| Ephemeral (root fs) | 50GB | Lost on restart |
| Persistent (`/data`) | 20GB-1TB | Paid tiers ($5-$100/mo) |
| Build cache | Varies | Can cause "storage limit exceeded" |

**Best practice**: Set `HF_HOME=/data/.huggingface` to cache models in persistent storage.

> ⚠️ **Important**: `HF_HOME` must be set in the Space's **Settings → Repository secrets** UI, not just in code. Environment variables set only in Python code won't persist across container restarts.

**Source**: [Spaces Persistent Storage](https://huggingface.co/docs/hub/en/spaces-storage)

### build limits

| Limit | Value | Notes |
|-------|-------|-------|
| Build timeout | 30-45 minutes | Large dependencies may fail |
| Build cache | Part of 50GB ephemeral | Can cause "storage limit exceeded" |
| Startup timeout | 30 minutes (default) | Configurable via `startup_duration_timeout` |
| Idle sleep | 48 hours | Free Spaces sleep after inactivity |

**Warning**: Heavy scientific stacks (PyTorch, large C extensions) may hit build timeout. Monitor build logs closely.

---

## gradio 6 constraints (december 2025)

> **Note**: Gradio 6.0 was released in late November 2025. Our codebase was written for Gradio 5.x but is largely compatible.

### key breaking changes from gradio 5 → 6

| Change | Gradio 5.x | Gradio 6.x | Our Status |
|--------|------------|------------|------------|
| Theme/CSS/JS placement | `gr.Blocks(theme=..., css=..., js=...)` | `demo.launch(theme=..., css=..., js=...)` | ✅ Already correct in `app.py:170` |
| HTML padding default | `padding=True` | `padding=False` | ⚠️ Minor visual change |
| Chatbot message format | Tuple `[["user", "bot"]]` | Dict `{"role": ..., "content": ...}` | N/A - Not used |
| `show_api` parameter | `show_api=True/False` | `footer_links=["api", "gradio", "settings"]` | N/A - Not customized |
| Event `api_name=False` | `api_name=False` | `api_visibility="private"` | N/A - Not used |

### new in gradio 6

1. **Custom Web Components**: Write custom components in pure HTML/JS inline in Python via `gradio cc`
2. **Vibe Mode**: `gradio --vibe app.py` for AI-assisted app editing
3. **Performance**: Significantly lighter and faster
4. **Security**: Trail of Bits audit improvements carried forward
5. **Server-Side Rendering (SSR)**: Faster initial loads, better SEO

> ⚠️ **SSR Consideration**: With SSR enabled, JavaScript that references `window` or `document` may fail during server-side render. Ensure NiiVue initialization checks `typeof window !== 'undefined'` before accessing browser APIs.

### javascript execution in `gr.HTML`

**CRITICAL ISSUE**: The `gr.HTML` component does **not** execute JavaScript in `<script>` tags in the standard way.

#### current implementation (viewer.py:262-324)

```python
def create_niivue_html(...) -> str:
    return f"""
    <div style="width:100%; height:{height}px; ...">
        <canvas id="niivue-canvas" style="width:100%; height:100%;"></canvas>
    </div>
    <script type="module">
        const niivueModule = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
        // ... NiiVue initialization
    </script>
    """
```

#### the problem

From the [Gradio documentation](https://www.gradio.app/guides/custom-CSS-and-JS) and [HF Forums](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316):

> "The `gr.HTML` component doesn't support loading scripts via traditional `<script>` tags. This prevents JavaScript functions from being accessible to inline event handlers."

#### recommended fix

Use `gr.Blocks(js=...)` or `demo.load(_js=...)` to inject JavaScript:

```python
NIIVUE_INIT_JS = """
async () => {
    // Wait for NiiVue module to load
    const niivueModule = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
    globalThis.Niivue = niivueModule.Niivue;
}
"""

def create_app() -> gr.Blocks:
    with gr.Blocks(js=NIIVUE_INIT_JS) as demo:
        # ... components

    return demo
```

Then in the HTML component, reference the global:

```python
def create_niivue_html(volume_url: str, ...) -> str:
    return f"""
    <div id="niivue-container-{uuid}" style="...">
        <canvas id="niivue-canvas-{uuid}"></canvas>
    </div>
    <script>
        (async function() {{
            if (typeof globalThis.Niivue === 'undefined') {{
                console.error('NiiVue not loaded');
                return;
            }}
            const nv = new globalThis.Niivue({{...}});
            await nv.attachTo('niivue-canvas-{uuid}');
            // ...
        }})();
    </script>
    """
```

**Note**: Even this may not work reliably. Testing on HF Spaces is required.

#### alternative: gradio custom components (`gradio cc`)

For production deployments, Gradio 6 supports first-class **Custom Components** via the `gradio cc` CLI. This is the recommended "production" solution (vs. the `js=` hack for MVP).

```bash
# Create a NiiVue custom component
gradio cc create NiiVueViewer --template HTML

# Development server with hot reload
gradio cc dev

# Build for distribution
gradio cc build

# Publish to PyPI and HF Spaces
gradio cc publish
```

**Pros**:
- First-class support, proper state management
- No hacky string interpolation
- Reusable across projects

**Cons**:
- Requires Node.js build step
- Higher complexity than `js=` parameter
- Overkill for MVP

**Source**: [Custom Components In Five Minutes](https://www.gradio.app/guides/custom-components-in-five-minutes)

#### alternative: `gradio-iframe` component

The [`gradio-iframe`](https://pypi.org/project/gradio-iframe/) package (v0.0.10) provides an iframe component that may execute JavaScript more reliably:

```python
from gradio_iframe import iFrame

viewer = iFrame(
    value="<html>...NiiVue code...</html>",
    label="NiiVue Viewer"
)
```

**Warning**: This is experimental and "not fully tested" per the maintainer. Use with caution.

### css restrictions

Custom CSS should use `elem_id` and `elem_classes` rather than query selectors:

> "The use of query selectors in custom JS and CSS is not guaranteed to work across Gradio versions as the Gradio HTML DOM may change."

**Source**: [Custom CSS and JS Guide](https://www.gradio.app/guides/custom-CSS-and-JS)

### security (gradio 5 audit, inherited by v6)

The Trail of Bits security audit was performed on **Gradio 5.0**. All fixes are inherited by Gradio 6.x:

- **CVE-2024-47872**: XSS via HTML/JS/SVG file uploads (fixed in 5.0.0)
- File type restrictions enforced server-side
- Our app uses `gradio>=6.0.0` - we're covered

> **Note**: There was no separate Gradio 6 audit. The security improvements from Gradio 5 persist in v6.

**Source**: [A Security Review of Gradio 5](https://huggingface.co/blog/gradio-5-security)

---

## readme.md yaml configuration

### required fields for gradio spaces

```yaml
---
title: Stroke DeepISLES Demo
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "6.0.2"  # Latest stable as of Dec 2025
python_version: "3.11"
app_file: app.py
pinned: false
license: mit
short_description: "Ischemic stroke lesion segmentation using DeepISLES"

# Optional but recommended
models:
  - isleschallenge/deepisles  # If we reference it
datasets:
  - YongchengYAO/ISLES24-MR-Lite
tags:
  - medical-imaging
  - stroke
  - segmentation
  - neuroimaging
  - niivue

# For CPU-only demo mode
suggested_hardware: cpu-basic

# If we need cross-origin isolation (e.g., SharedArrayBuffer)
# custom_headers:
#   cross-origin-embedder-policy: require-corp
#   cross-origin-opener-policy: same-origin
---
```

### configuration reference

| Field | Type | Description |
|-------|------|-------------|
| `sdk` | string | `gradio`, `docker`, or `static` |
| `sdk_version` | string | Gradio version (e.g., "5.0.0") |
| `python_version` | string | Python version (e.g., "3.11") |
| `app_file` | string | Entry point (default: `app.py`) |
| `suggested_hardware` | string | Hardware for duplicators |
| `disable_embedding` | bool | Prevent iframe embedding |
| `custom_headers` | dict | COEP/COOP/CORP headers |

**Source**: [Spaces Configuration Reference](https://huggingface.co/docs/hub/en/spaces-config-reference)

---

## dependencies

### requirements.txt for hf spaces

HF Spaces uses `requirements.txt`, not `pyproject.toml` for dependency installation.

```text
# requirements.txt for HF Spaces

# Core - Tobias's fork with BIDS + NIfTI lazy loading
git+https://github.com/CloseChoice/datasets.git@feat/bids-loader-streaming-upload-fix

# HuggingFace
huggingface-hub>=0.25.0

# NIfTI handling
nibabel>=5.2.0
numpy>=1.26.0

# Configuration
pydantic>=2.5.0
pydantic-settings>=2.1.0

# UI - Gradio 6.x (latest stable as of Dec 2025)
gradio>=6.0.0,<7.0.0
matplotlib>=3.8.0

# Networking
requests>=2.0.0
```

### potential issues

1. **Git dependencies**: HF Spaces supports `git+https://...` in requirements.txt
2. **C extensions**: nibabel/numpy compile fine on HF Spaces
3. **Size**: No bloated dependencies (no PyTorch required for demo mode)

---

## deployment paths

### hardware requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| GPU | NVIDIA with CUDA 11.3+ | **Mandatory** - no CPU/MPS fallback |
| VRAM | 4GB minimum, 12GB+ recommended | For parallel processing |
| Docker | Docker + nvidia-container-toolkit | Required for DeepISLES |
| Python | 3.8+ (3.11 recommended) | Per project config |

> ⚠️ **Apple Silicon (M1/M2/M3) is NOT supported.** DeepISLES requires NVIDIA CUDA.

### path 1: local nvidia gpu (primary development)

For day-to-day development and testing on your own NVIDIA GPU machine.

```bash
# 1. Ensure Docker + nvidia-container-toolkit installed
docker run --rm --gpus all nvidia/cuda:11.3-base nvidia-smi

# 2. Pull DeepISLES image
docker pull isleschallenge/deepisles

# 3. Run the app
uv run python -m stroke_deepisles_demo.ui.app
```

**Pros**:
- Free (you own the hardware)
- Fast iteration
- No network dependency

**Cons**:
- Requires NVIDIA GPU hardware

### path 2: hf spaces docker sdk + gpu (on-demand demos)

For showcasing to others. Spin up when needed, pause when done.

#### dockerfile for hf spaces

```dockerfile
# Dockerfile for HF Spaces
FROM isleschallenge/deepisles:latest

# Add our application
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY src/ /app/src/
COPY app.py /app/

WORKDIR /app
EXPOSE 7860
CMD ["python", "-m", "stroke_deepisles_demo.ui.app"]
```

#### readme.md configuration

```yaml
---
title: Stroke DeepISLES Demo
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
suggested_hardware: t4-small
pinned: false
license: mit
---
```

#### cost management: pause/restart api

```python
from huggingface_hub import HfApi

api = HfApi()
SPACE_ID = "your-username/stroke-deepisles-demo"

# PAUSE - stops billing immediately
api.pause_space(SPACE_ID)

# RESTART - spin up for demo
api.restart_space(SPACE_ID)

# AUTO-SLEEP after 30 min inactivity
api.set_space_sleep_time(SPACE_ID, sleep_time=1800)
```

#### billing breakdown

| State | Billed? | How to Enter |
|-------|---------|--------------|
| Running | ✅ $0.40/hr (T4) | `restart_space()` or visitor wakes it |
| Sleeping | ❌ $0 | Auto after `sleep_time` inactivity |
| Paused | ❌ $0 | `pause_space()` - only owner can restart |

**Typical demo session**: 30-60 minutes = **$0.20-$0.40**

**Monthly cost if paused**: **$0.00**

---

## niivue integration analysis

### current implementation

Our viewer uses NiiVue loaded from unpkg CDN with base64 data URLs:

```python
# viewer.py:289-324
return f"""
<div style="width:100%; height:{height}px; ...">
    <canvas id="niivue-canvas" style="width:100%; height:100%;"></canvas>
</div>
<script type="module">
    const niivueModule = await import('https://unpkg.com/@niivue/niivue@0.65.0/dist/index.js');
    const Niivue = niivueModule.Niivue;
    // ...
    await nv.loadVolumes(volumes);
</script>
"""
```

### potential issues

1. **Script execution**: `<script type="module">` may not execute in `gr.HTML`
2. **Canvas element IDs**: Hardcoded `id="niivue-canvas"` will conflict if multiple viewers
3. **CSP headers**: External CDN might be blocked by Content Security Policy
4. **Memory**: Base64 NIfTI files loaded entirely into browser memory

### recommended fixes

```python
import uuid

def create_niivue_html(volume_url: str, mask_url: str | None = None, *, height: int = 400) -> str:
    """Create HTML/JS for NiiVue viewer with unique IDs."""
    canvas_id = f"niivue-canvas-{uuid.uuid4().hex[:8]}"

    # ... rest of implementation with unique canvas_id
```

### webgl compatibility

NiiVue requires WebGL2. Most modern browsers support it, but:

- HF Spaces renders in iframes
- Some iframe security policies restrict WebGL
- Cross-origin isolation may be needed for SharedArrayBuffer

**Test required**: Verify NiiVue WebGL works in HF Spaces iframe environment.

---

## memory and performance

### memory considerations

| Resource | Size | Concern |
|----------|------|---------|
| DWI NIfTI (ISLES24-MR-Lite) | ~2-5 MB | Low |
| Base64 encoded | ~3-7 MB | ~1.33x overhead |
| Multiple volumes in browser | ~15-20 MB | Moderate |
| Matplotlib figures | ~1-5 MB | Low |
| Free tier RAM | 16 GB | Sufficient |

### optimization strategies

1. **Lazy loading**: Don't load all cases at startup
2. **Cleanup**: Clear matplotlib figures after rendering
3. **Pagination**: Limit case dropdown to reasonable number
4. **Compression**: NIfTI files are already gzipped

---

## testing checklist

Before deploying to HF Spaces, verify:

### local testing

- [ ] `uv run python app.py` launches without errors
- [ ] Case dropdown populates
- [ ] NiiVue viewer renders (in browser, not headless)
- [ ] Matplotlib plots display correctly
- [ ] No import-time side effects (network calls)

### hf spaces testing

- [ ] Create private Space first
- [ ] Verify dependencies install
- [ ] Check JavaScript execution in `gr.HTML`
- [ ] Test NiiVue WebGL rendering
- [ ] Monitor memory usage
- [ ] Test on mobile browsers (if applicable)

### known issues to monitor

1. **Startup timeout**: Default is 30 minutes, may need adjustment
2. **Sleep behavior**: Free Spaces sleep after 48h of inactivity
3. **Build cache**: May cause "storage limit exceeded"

---

## deployment procedure

### step 1: verify local nvidia gpu setup

```bash
# Verify NVIDIA driver and Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.3-base nvidia-smi

# Pull DeepISLES image
docker pull isleschallenge/deepisles

# Test local inference
uv run stroke-demo run --case sub-stroke0001
```

### step 2: create dockerfile for hf spaces

```dockerfile
# Dockerfile
FROM isleschallenge/deepisles:latest

# Install additional dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY src/ /app/src/
COPY app.py /app/

WORKDIR /app
EXPOSE 7860

CMD ["python", "-m", "stroke_deepisles_demo.ui.app"]
```

### step 3: create requirements.txt

```bash
cat > requirements.txt << 'EOF'
git+https://github.com/CloseChoice/datasets.git@feat/bids-loader-streaming-upload-fix
huggingface-hub>=0.25.0
nibabel>=5.2.0
numpy>=1.26.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
gradio>=6.0.0,<7.0.0
matplotlib>=3.8.0
requests>=2.0.0
EOF
```

### step 4: update readme.md for docker sdk

```yaml
---
title: Stroke DeepISLES Demo
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
suggested_hardware: t4-small
pinned: false
license: mit
---
```

### step 5: deploy to private space

```bash
# Create Docker Space with GPU
huggingface-cli repo create stroke-deepisles-demo --type space --sdk docker

# Push code
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/stroke-deepisles-demo
git push space main
```

### step 6: configure cost management

```python
from huggingface_hub import HfApi

api = HfApi()
SPACE_ID = "YOUR_USERNAME/stroke-deepisles-demo"

# Set auto-sleep after 30 min of inactivity
api.set_space_sleep_time(SPACE_ID, sleep_time=1800)

# After demo: pause to stop all billing
api.pause_space(SPACE_ID)

# Before next demo: restart
api.restart_space(SPACE_ID)
```

### step 7: monitor and iterate

- Check build logs (Docker builds can take 10-20 min)
- Test inference end-to-end
- Verify NiiVue visualization works
- Pause Space when done testing

---

## decision matrix

| Approach | Real Inference | Cost | Complexity | Use Case |
|----------|----------------|------|------------|----------|
| Local NVIDIA GPU | ✅ | $0 | Low | **Primary development** |
| HF Spaces Docker + GPU (on-demand) | ✅ | ~$0.40/demo | Medium | **Showcasing to others** |
| ~~Demo Mode (pre-computed)~~ | ❌ Fake | $0 | Low | ~~Rejected - defeats purpose~~ |
| ~~HF Spaces Gradio SDK (free)~~ | ❌ No Docker | $0 | Low | ~~Cannot run DeepISLES~~ |
| ~~ZeroGPU (free H200)~~ | ❌ No Docker | $0 | Low | ~~Only supports Gradio SDK~~ |

---

## sources

### official documentation
- [Gradio Spaces](https://huggingface.co/docs/hub/en/spaces-sdks-gradio)
- [Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)
- [Custom CSS and JS](https://www.gradio.app/guides/custom-CSS-and-JS)
- [Custom Components In Five Minutes](https://www.gradio.app/guides/custom-components-in-five-minutes)
- [Spaces Configuration Reference](https://huggingface.co/docs/hub/en/spaces-config-reference)
- [Spaces Persistent Storage](https://huggingface.co/docs/hub/en/spaces-storage)
- [Manage Spaces - HF Hub](https://huggingface.co/docs/huggingface_hub/main/en/guides/manage-spaces)
- [A Security Review of Gradio 5](https://huggingface.co/blog/gradio-5-security)
- [Trail of Bits Gradio Audit](https://blog.trailofbits.com/2024/10/10/auditing-gradio-5-hugging-faces-ml-gui-framework/)
- [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [ZeroGPU Documentation](https://huggingface.co/docs/hub/en/spaces-zerogpu)

### forum discussions (cold start verification)
- [Slow Space Cold Boot](https://discuss.huggingface.co/t/slow-space-cold-boot/72154) - 2 min baseline confirmed
- [T4 startup taking 45+ minutes](https://discuss.huggingface.co/t/staring-up-t4-instances-is-taking-45-minutes/139567) - Feb 2025 resource issues
- [Space stuck at Starting](https://discuss.huggingface.co/t/hf-space-stuck-at-starting/170911) - Nov 2025 edge case
- [Space stuck in Paused](https://discuss.huggingface.co/t/space-stuck-in-paused/169467) - Oct 2025 edge case
- [ZeroGPU Docker request](https://huggingface.co/spaces/zero-gpu-explorers/README/discussions/27) - Community asking for Docker support
- [Gradio HTML component with javascript code don't work](https://discuss.huggingface.co/t/gradio-html-component-with-javascript-code-dont-work/37316)

### packages
- [NiiVue npm package](https://www.npmjs.com/package/@niivue/niivue) - v0.65.0 (latest as of Dec 2025)
- [gradio-iframe PyPI](https://pypi.org/project/gradio-iframe/) - v0.0.10 (experimental)
- [DeepISLES Docker Hub](https://hub.docker.com/r/isleschallenge/deepisles)

---

## appendix: friction points summary

### high priority (must fix before deployment)

1. **JavaScript execution in `gr.HTML`**
   - Current: `<script type="module">` embedded in HTML string
   - Risk: May not execute at all
   - Fix: Use `gr.Blocks(js=...)` or `demo.load(_js=...)`
   - Testing: Required on actual HF Spaces environment

2. **Docker + GPU requirement**
   - Current: Pipeline requires `isleschallenge/deepisles` container with NVIDIA GPU
   - Risk: Gradio SDK cannot run Docker; Apple Silicon not supported
   - Fix: Use Docker SDK with GPU hardware (on-demand billing)

### medium priority (should fix)

3. **Unique canvas IDs**
   - Current: Hardcoded `id="niivue-canvas"`
   - Risk: Multiple viewers would conflict
   - Fix: Generate unique IDs with UUID

4. **Git dependency in requirements**
   - Current: `datasets @ git+https://...` in pyproject.toml
   - Risk: HF Spaces uses requirements.txt
   - Fix: Create requirements.txt with git URL

### low priority (nice to have)

5. **Memory optimization**
   - Current: Full NIfTI files in base64
   - Risk: Could hit memory limits on complex cases
   - Fix: Implement streaming or pagination

6. **CDN reliability**
   - Current: NiiVue from unpkg.com
   - Risk: CDN downtime affects app
   - Fix: Consider bundling or alternative CDN

---

## appendix: operational runbook

### daily operations

**After development session:**
```bash
# Always pause to stop billing
python -c "
from huggingface_hub import HfApi
api = HfApi()
api.pause_space('YOUR_USERNAME/stroke-deepisles-demo')
print('Space paused - billing stopped')
"
```

**Before scheduled demo:**
```bash
# T-30 minutes: Start warm-up
python -c "
from huggingface_hub import HfApi
api = HfApi()
api.restart_space('YOUR_USERNAME/stroke-deepisles-demo')
print('Warming up... check status in 5 min')
"

# T-25, T-20, T-15, T-10, T-5 minutes: Check status
python -c "
from huggingface_hub import HfApi
api = HfApi()
info = api.space_info('YOUR_USERNAME/stroke-deepisles-demo')
print(f'Status: {info.runtime.stage}')
# BUILDING -> Wait
# RUNNING_BUILDING -> Almost ready
# RUNNING -> Ready to demo!
"
```

**After demo:**
```bash
# Immediately pause to stop billing
python -c "
from huggingface_hub import HfApi
api = HfApi()
api.pause_space('YOUR_USERNAME/stroke-deepisles-demo')
print('Demo complete - billing stopped')
"
```

### troubleshooting

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| Status stuck on "BUILDING" > 45 min | Build timeout | Check build logs, optimize Dockerfile |
| Status stuck on "STARTING" > 30 min | Resource issue | Factory rebuild, or try different hardware |
| Status stuck on "PAUSED" after restart | API issue | Wait 5 min, retry, or use UI |
| "Scheduling failure" error | GPU unavailable | Try later or different hardware tier |
| "Storage limit exceeded" | Build cache full | Clear cache, reduce image layers |

### cost tracking

```bash
# Check current month's usage
# Visit: https://huggingface.co/settings/billing

# Estimate cost per demo:
# T4-small: $0.40/hr × 0.5 hr = $0.20 per 30-min demo
# T4-medium: $0.60/hr × 0.5 hr = $0.30 per 30-min demo
# A10G-small: $1.05/hr × 0.5 hr = $0.53 per 30-min demo
```

---

## next steps

> **Status**: Spec APPROVED - Ready for implementation

1. ~~Senior Review: Get approval on this spec~~ ✅ **APPROVED**
2. **Local Testing**: Verify full pipeline on local NVIDIA GPU machine
3. **Fix JavaScript Pattern**: Refactor NiiVue initialization for `gr.HTML`
4. **Create Dockerfile**: Build HF Spaces Docker image based on DeepISLES
5. **Create requirements.txt**: Generate from pyproject.toml
6. **Deploy to Private Space**: Test Docker SDK + GPU on HF Spaces
7. **Configure Auto-Sleep**: Set `sleep_time=1800` (30 min) to minimize costs
8. **Pre-Demo Test**: Practice warm-up procedure (20-30 min cold start)
9. **Demo & Pause**: Show to stakeholders, then `pause_space()` to stop billing
10. **Public Release**: Make Space public when stable (keep paused when not demoing)
