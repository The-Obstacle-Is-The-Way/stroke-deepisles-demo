# context: stroke-deepisles-demo

> **Disclaimer**: This software is for research and demonstration purposes only. Not for clinical use.

## overview

This document explains **why** we're building `stroke-deepisles-demo` and the architectural context that informs our design decisions.

## the problem we're solving

We want to demonstrate an end-to-end neuroimaging inference pipeline:

```
HuggingFace Hub (ISLES24-MR-Lite)
        ↓
    BIDS/NIfTI loader (datasets fork)
        ↓
    DeepISLES Docker (stroke segmentation)
        ↓
    NiiVue visualization (Gradio Space)
```

This showcases that:
1. Neuroimaging data can be consumed from HF Hub with proper BIDS/NIfTI support
2. Clinical-grade models can run via Docker as black boxes
3. Results can be visualized interactively in a browser

## why we need tobias's datasets fork

As of December 2025, the official `huggingface/datasets` library has **partial** NIfTI support but lacks critical features for neuroimaging workflows.

### what's merged upstream

| PR | Author | Status | Description |
|----|--------|--------|-------------|
| [#7874](https://github.com/huggingface/datasets/pull/7874) | CloseChoice (Tobias) | Merged Nov 21 | NIfTI visualization support |
| [#7878](https://github.com/huggingface/datasets/pull/7878) | CloseChoice (Tobias) | Merged Nov 27 | Replace papaya with NiiVue |

### what's NOT merged (and why we need the fork)

| PR | Author | Status | Description |
|----|--------|--------|-------------|
| [#7886](https://github.com/huggingface/datasets/pull/7886) | The-Obstacle-Is-The-Way | Open | **BIDS dataset loader** - `load_dataset('bids', ...)` |
| [#7887](https://github.com/huggingface/datasets/pull/7887) | The-Obstacle-Is-The-Way | Open | **NIfTI lazy loading fix** - use `dataobj` not `get_fdata()` |
| [#7892](https://github.com/huggingface/datasets/pull/7892) | CloseChoice (Tobias) | Open | **NIfTI encoding for lazy upload** - fixes Arrow serialization |

The fork branch bundles all these features:
```
https://github.com/CloseChoice/datasets/tree/feat/bids-loader-streaming-upload-fix
```

We pin to this branch until upstream merges the PRs.

## key components

### 1. data source: ISLES24-MR-Lite

- **HF Dataset**: [YongchengYAO/ISLES24-MR-Lite](https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite)
- **Content**: 149 acute stroke MRI cases with DWI, ADC, and manual infarct masks
- **Origin**: Subset of ISLES 2024 challenge data
- **Why suitable**: DeepISLES was trained on ISLES 2022, so ISLES24 is an **external** test set (no data leakage)

### 2. model: DeepISLES

- **Paper**: Nature Communications 2025 - "DeepISLES: A clinically validated ischemic stroke segmentation model"
- **GitHub**: [ezequieldlrosa/DeepIsles](https://github.com/ezequieldlrosa/DeepIsles)
- **Docker**: `isleschallenge/deepisles`
- **Inputs**: DWI + ADC (required), FLAIR (optional)
- **Output**: 3D binary lesion mask (NIfTI)
- **Mode**: We use `fast=True` (single model) not the full 3-model ensemble

### 3. visualization: NiiVue

- **Library**: [niivue/niivue](https://github.com/niivue/niivue)
- **Type**: WebGL2-based neuroimaging viewer
- **Formats**: Native NIfTI support, overlays, multiplanar views
- **Integration**: Via Gradio custom HTML component or iframe

### 4. UI framework: Gradio 5

- **Version**: Gradio 5.x (latest as of Dec 2025)
- **Features**: SSR for fast loading, improved components, WebRTC support
- **Deployment**: Hugging Face Spaces

## architecture diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     stroke-deepisles-demo                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  data/       │    │  inference/  │    │  ui/         │       │
│  │              │    │              │    │              │       │
│  │  - loader    │───▶│  - docker    │───▶│  - gradio    │       │
│  │  - adapter   │    │  - wrapper   │    │  - niivue    │       │
│  │  - staging   │    │  - pipeline  │    │  - viewer    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                    core/                              │       │
│  │  - config (pydantic-settings)                        │       │
│  │  - types (dataclasses, TypedDicts)                   │       │
│  │  - exceptions                                         │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   ┌──────────┐        ┌──────────┐         ┌──────────┐
   │ HF Hub   │        │ Docker   │         │ Browser  │
   │ datasets │        │ Engine   │         │ WebGL2   │
   └──────────┘        └──────────┘         └──────────┘
```

## design principles

1. **Vertical slices**: Each phase delivers runnable functionality
2. **TDD**: Tests written before implementation
3. **Type safety**: Full type hints, mypy/pyright strict mode
4. **Separation of concerns**: Data, inference, and UI are independent modules
5. **Docker as black box**: We don't reimplement DeepISLES, we call it
6. **Graceful degradation**: Mock Docker for tests, fallback viewers if NiiVue fails

## reference repositories

These are cloned locally (without git linkages) for reference:

| Directory | Source | Purpose |
|-----------|--------|---------|
| `_reference_repos/datasets-tobias-bids-fork/` | CloseChoice/datasets@feat/bids-loader-streaming-upload-fix | BIDS loader + NIfTI lazy loading |
| `_reference_repos/arc-aphasia-bids/` | The-Obstacle-Is-The-Way/arc-aphasia-bids | BIDS upload patterns (reference only) |
| `_reference_repos/DeepIsles/` | ezequieldlrosa/DeepIsles | DeepISLES CLI interface reference |
| `_reference_repos/bids-neuroimaging-space/` | [TobiasPitters/bids-neuroimaging](https://huggingface.co/spaces/TobiasPitters/bids-neuroimaging) | **Working NiiVue + FastAPI implementation** |

### key reference: tobias's bids-neuroimaging space

This is the most important reference for Phase 4 (UI). It demonstrates:

1. **NiiVue working in HF Spaces** - Proof that WebGL2 viewer works in production
2. **FastAPI + raw HTML approach** - Clean, no Gradio overhead for viewer
3. **Base64 data URLs for NIfTI** - `data:application/octet-stream;base64,{b64}`
4. **NiiVue CDN loading** - `https://unpkg.com/@niivue/niivue@0.57.0/dist/index.js`
5. **Multiplanar + 3D rendering** - `setSliceType(sliceTypeMultiplanar)` + `setMultiplanarLayout(2)`

Key file: `main.py` (~485 lines) - complete working implementation.

## sources

- [uv project configuration](https://docs.astral.sh/uv/concepts/projects/config/)
- [Python packaging guide - pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Real Python - Managing projects with uv](https://realpython.com/python-uv/)
- [Gradio 5 announcement](https://huggingface.co/blog/gradio-5)
- [NiiVue GitHub](https://github.com/niivue/niivue)
- [Gradio custom HTML components](https://www.gradio.app/guides/custom_HTML_components)
