# Data Directory

This folder is for local development data only. The primary data source is HuggingFace.

## Data Source

**Primary**: [hugging-science/isles24-stroke](https://huggingface.co/datasets/hugging-science/isles24-stroke)

The dataset is automatically downloaded and cached by HuggingFace when you run:

```python
from stroke_deepisles_demo.data import load_isles_dataset

# Loads from HuggingFace (default)
dataset = load_isles_dataset()

# Access cases
case = dataset.get_case(0)  # or dataset.get_case("sub-stroke0001")
```

## HuggingFace Cache Location

Data is cached at: `~/.cache/huggingface/datasets/hugging-science___isles24-stroke/`

## Dataset Contents

149 acute ischemic stroke cases with:
- **Imaging**: DWI, ADC, CT, CTA, perfusion maps (tmax, mtt, cbf, cbv)
- **Masks**: lesion_mask, lvo_mask, cow_segmentation
- **Clinical**: age, sex, nihss_admission, mrs_admission, mrs_3month

## Local Development (Optional)

For offline development, you can still use a local directory:

```python
dataset = load_isles_dataset("path/to/local/data", local_mode=True)
```

Expected structure for local mode:
```text
data/
├── Images-DWI/     # DWI volumes
├── Images-ADC/     # ADC maps
└── Masks/          # Ground truth lesion masks
```

## Notes

- All data files are gitignored
- On HuggingFace Spaces, data loads automatically from the HF cache
- See dataset card for citation requirements
