# context: stroke-deepisles-demo

> **Disclaimer**: This software is for research and demonstration purposes only. Not for clinical use.

## overview

This document explains **why** we're building `stroke-deepisles-demo` and the architectural context that informs our design decisions.

## the problem we're solving

We want to demonstrate an end-to-end neuroimaging inference pipeline:

```
CURRENT (Phase 1A):
    Local NIfTI files (extracted from ISLES24-MR-Lite ZIPs)
            ↓
        File-based loader (parse BIDS filenames)
            ↓
        DeepISLES Docker (stroke segmentation)
            ↓
        NiiVue visualization (Gradio Space)

FUTURE (Phase 1C-D):
    HuggingFace Hub (properly uploaded dataset)
            ↓
        Tobias's datasets fork (BIDS loader + Nifti feature)
            ↓
        DeepISLES Docker (stroke segmentation)
            ↓
        NiiVue visualization (Gradio Space)
```

This showcases that:
1. Neuroimaging data can be loaded from local BIDS-named files (NOW)
2. Neuroimaging data can be consumed from HF Hub with proper BIDS/NIfTI support (FUTURE)
3. Clinical-grade models can run via Docker as black boxes
4. Results can be visualized interactively in a browser

## critical discovery (2025-12-04)

**The original ISLES24-MR-Lite dataset is NOT properly uploaded to HuggingFace.**

It's just raw ZIP files dumped on HF, not a proper Dataset with parquet/Arrow format. This means `load_dataset()` fails. See `data/discovery/isles24_schema_report.txt` for full details.

**Workaround**: We extracted the ZIPs locally to `data/isles24/` (git-ignored) and will implement a file-based loader first. Later, we'll re-upload properly and verify full HF consumption.

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

- **HF Dataset**: [YongchengYAO/ISLES24-MR-Lite](https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite) (**BROKEN** - raw ZIPs, not proper dataset)
- **Local extracted**: `data/isles24/` (git-ignored)
- **Content**: 149 acute stroke MRI cases with DWI, ADC, and manual infarct masks
- **Origin**: Subset of ISLES 2024 challenge data
- **Why suitable**: DeepISLES was trained on ISLES 2022, so ISLES24 is an **external** test set (no data leakage)

**File structure** (after extraction):
```
data/isles24/
├── Images-DWI/sub-stroke{XXXX}_ses-02_dwi.nii.gz        # 149 files
├── Images-ADC/sub-stroke{XXXX}_ses-02_adc.nii.gz        # 149 files
└── Masks/sub-stroke{XXXX}_ses-02_lesion-msk.nii.gz      # 149 files
```

**Schema reference**: `data/discovery/isles24_schema_report.txt`

### 2. model: DeepISLES

- **Paper**: Nature Communications 2025 - "DeepISLES: A clinically validated ischemic stroke segmentation model"
- **GitHub**: [ezequieldlrosa/DeepIsles](https://github.com/ezequieldlrosa/DeepIsles)
- **Docker**: `isleschallenge/deepisles`
- **Inputs**: DWI + ADC (required), FLAIR (required for ensemble, optional for fast mode)
- **Output**: 3D binary lesion mask (NIfTI)
- **Mode**: `fast=True` runs **SEALS only** (the ISLES'22 challenge winner)

#### Why we use `fast=True` (SEALS-only mode)

DeepISLES is an ensemble of 3 models from the ISLES'22 challenge:

| Model | Based On | Inputs Required | Notes |
|-------|----------|-----------------|-------|
| **SEALS** | nnUNet | DWI + ADC | 🏆 **ISLES'22 Winner** - runs in `--fast` mode |
| NVAUTO | MONAI Auto3dseg | DWI + ADC + FLAIR | Requires FLAIR |
| SWAN | FACTORIZER | DWI + ADC + FLAIR | Requires FLAIR |

**Key insight**: ISLES24-MR-Lite contains only DWI + ADC (no FLAIR). Therefore:
- `--fast True` → Runs SEALS only → **Perfect match** for our dataset
- `--fast False` → Would try to run all 3 models → NVAUTO/SWAN would fail without FLAIR

This is **not a downgrade**. SEALS won the ISLES'22 challenge and is state-of-the-art for stroke lesion segmentation using DWI+ADC alone.

#### Scientific validity: External validation with zero data leakage

| Dataset | Year | Used For |
|---------|------|----------|
| **ISLES 2022** | 2022 | SEALS training data (250 cases) |
| **ISLES 2024** | 2024 | Our test data (149 cases from MR-Lite) |

- Different patient cohorts (2 years apart, different hospitals)
- SEALS has **never seen** ISLES24 patients
- We have ground truth masks → can validate predictions
- This constitutes a legitimate **external validation study**

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
