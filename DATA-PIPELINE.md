# Data Pipeline

> **The Problem:** HuggingFace `datasets` doesn't natively support NIfTI/BIDS neuroimaging formats.
> **The Solution:** `neuroimaging-go-brrrr` extends `datasets` with `Nifti()` feature type.

---

## What is neuroimaging-go-brrrr?

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│              neuroimaging-go-brrrr EXTENDS HUGGINGFACE DATASETS                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   pip install datasets              pip install neuroimaging-go-brrrr           │
│   ───────────────────────           ─────────────────────────────────           │
│   Standard HuggingFace              EXTENDS datasets with:                      │
│   • Images, text, audio             • Nifti() feature type for .nii.gz          │
│   • Parquet/Arrow storage           • BIDS directory parsing                    │
│   • Hub integration                 • Upload utilities (BIDS→Hub)               │
│                                     • Validation utilities                      │
│                                     • Bug workarounds for upstream issues       │
│                                                                                 │
│   When you install neuroimaging-go-brrrr, you get:                              │
│   • A patched datasets library with Nifti() support (pinned git commit)         │
│   • bids_hub module for upload/validation                                       │
│   • All upstream bug workarounds in one place                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key insight:** `neuroimaging-go-brrrr` pins to a specific commit of `datasets` that includes `Nifti()` support:

```toml
# From neuroimaging-go-brrrr/pyproject.toml
[tool.uv.sources]
datasets = { git = "https://github.com/huggingface/datasets.git", rev = "004a5bf4..." }
```

---

## The Two Pipelines

### Pipeline 1: UPLOAD (How Data Gets to HuggingFace)

```text
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Local BIDS     │     │  neuroimaging-go-    │     │   HuggingFace Hub   │
│  Directory      │ ──► │  brrrr (bids_hub)    │ ──► │   hugging-science/  │
│  (Zenodo)       │     │                      │     │   isles24-stroke    │
└─────────────────┘     │  • build_isles24_    │     └─────────────────────┘
                        │    file_table()      │
                        │  • Nifti() features  │
                        │  • push_to_hub()     │
                        └──────────────────────┘
```

### Pipeline 2: CONSUMPTION (How This Demo Loads Data)

**THE CORRECT PATTERN:**

```python
from datasets import load_dataset

# neuroimaging-go-brrrr provides the patched datasets with Nifti() support
ds = load_dataset("hugging-science/isles24-stroke", split="train")

# Access data - Nifti() handles lazy loading automatically
example = ds[0]
dwi = example["dwi"]           # numpy array
adc = example["adc"]           # numpy array
lesion_mask = example["lesion_mask"]  # numpy array
```

This is the **intended consumption pattern**. It should just work because:
1. `neuroimaging-go-brrrr` provides the patched `datasets` with `Nifti()` support
2. The dataset was uploaded with `Nifti()` features
3. `load_dataset()` automatically handles lazy loading

---

## Current State: REFACTOR NEEDED

**Problem:** stroke-deepisles-demo currently has a hand-rolled workaround in `data/adapter.py` that bypasses `datasets.load_dataset()`. This workaround uses `HfFileSystem` + `pyarrow` directly to download individual parquet files.

**Why this is wrong:**
1. Duplicates bug workarounds that should live in `neuroimaging-go-brrrr`
2. Doesn't use the `Nifti()` feature type properly
3. Harder to maintain - fixes need to happen in multiple places

**The fix:**
1. Delete the custom `HuggingFaceDataset` adapter in `data/adapter.py`
2. Use standard `datasets.load_dataset()` consumption pattern
3. If there are bugs, fix them in `neuroimaging-go-brrrr`, not locally

---

## Dependency Relationship

```text
stroke-deepisles-demo (this repo)
        │
        └── neuroimaging-go-brrrr @ v0.2.1
                │
                └── datasets @ git commit 004a5bf4... (patched with Nifti())
                └── huggingface-hub
                └── bids_hub module (upload + validation utilities)
```

**The consumption should flow through the standard pattern:**

```text
stroke-deepisles-demo
        │
        │ from datasets import load_dataset
        │ ds = load_dataset("hugging-science/isles24-stroke")
        ▼
neuroimaging-go-brrrr (provides patched datasets)
        │
        │ Nifti() feature type handles lazy loading
        ▼
HuggingFace Hub (isles24-stroke dataset)
```

---

## Dataset Info

| Property | Value |
|----------|-------|
| Dataset ID | `hugging-science/isles24-stroke` |
| Subjects | 149 |
| Modalities | DWI, ADC, Lesion Mask, NCCT, CTA, CTP, Perfusion Maps |
| Source | [Zenodo 17652035](https://zenodo.org/records/17652035) |

---

## What bids_hub Provides

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    neuroimaging-go-brrrr (bids_hub)                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   FOR UPLOADING:                       FOR CONSUMING:                           │
│   ──────────────                       ──────────────                           │
│   build_isles24_file_table()           Patched datasets with Nifti()            │
│   get_isles24_features()               └── Use standard load_dataset()          │
│   push_dataset_to_hub()                                                         │
│                                        validate_isles24_download()              │
│   We DON'T use these in this demo.     └── ISLES24_EXPECTED_COUNTS              │
│   Dataset already uploaded.            └── Can use for sanity checking          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [neuroimaging-go-brrrr](https://github.com/The-Obstacle-Is-The-Way/neuroimaging-go-brrrr)
- [isles24-stroke dataset card](https://huggingface.co/datasets/hugging-science/isles24-stroke)

---

## TODO: Refactor Data Loading

The current hand-rolled adapter in `data/adapter.py` should be replaced with standard `datasets.load_dataset()` consumption. This refactor should:

1. Remove `HuggingFaceDataset` class from `data/adapter.py`
2. Update `data/loader.py` to use `datasets.load_dataset()`
3. Remove pre-computed constants in `data/constants.py` (no longer needed)
4. Test that `Nifti()` lazy loading works correctly
5. If bugs are found, report/fix them in `neuroimaging-go-brrrr`
