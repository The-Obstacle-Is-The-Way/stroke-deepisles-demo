# Data Directory

This folder contains local neuroimaging data for the stroke-deepisles-demo project.

## Structure

```
data/
├── README.md           # This file (tracked)
├── isles24/            # ISLES24 NIfTI files (gitignored)
│   ├── Images-DWI/     # DWI volumes (149 files)
│   ├── Images-ADC/     # ADC maps (149 files)
│   └── Masks/          # Ground truth lesion masks (149 files)
└── discovery/          # Schema reports (gitignored)
    └── isles24_schema_report.txt
```

## Setup

1. Download ISLES24-MR-Lite from [HuggingFace](https://huggingface.co/datasets/YongchengYAO/ISLES24-MR-Lite)
2. Extract the ZIP files into `data/isles24/`:
   - `Images-DWI.zip` → `data/isles24/Images-DWI/`
   - `Images-ADC.zip` → `data/isles24/Images-ADC/`
   - `Masks.zip` → `data/isles24/Masks/`

## File Naming Convention

Files follow BIDS-like naming:
```
sub-stroke{XXXX}_ses-02_{modality}.nii.gz
```

Example: `sub-stroke0005_ses-02_dwi.nii.gz`

## Notes

- All data files are gitignored to avoid committing large binaries
- The `discovery/` folder contains schema reports from data exploration scripts
- See `docs/specs/02-phase-1-data-access.md` for detailed data loading documentation
