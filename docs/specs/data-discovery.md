# data discovery & verification protocol

## purpose
To establish a rigorous, reproducible process for exploring, verifying, and documenting external data sources (Hugging Face Datasets, BIDS repos, etc.) before integrating them into the production codebase. This prevents "schema guessing" and ensures strict typing aligns with reality.

## principles
1.  **No Assumptions**: Never assume column names, file formats, or data types. Verify them programmatically.
2.  **Isolation**: Discovery scripts and their outputs must be isolated from production code and source control.
3.  **Reproducibility**: The discovery process must be scriptable and reproducible, not a series of manual CLI commands.

## standard locations

### scripts
All discovery logic resides in:
```
scripts/discovery/
├── __init__.py
├── inspect_hf_dataset.py   # e.g., Generic HF inspector
├── verify_bids_layout.py   # e.g., BIDS validator
└── ...
```

### data & artifacts
All downloaded samples, temporary outputs, and schema reports reside in:
```
data/
├── isles24/             # Extracted ISLES24 data (IGNORED)
└── discovery/           # Schema reports, samples (IGNORED)
```

## discovery workflow

### 1. implementation
Write a focused script in `scripts/discovery/` that:
- Connects to the data source (e.g., HF Hub).
- Fetches *metadata* or a *minimal sample* (streaming mode preferred).
- Prints/Logs:
    - Feature keys (column names).
    - Data types (Arrow types, Python types).
    - Non-null counts (if feasible).
    - A sample row structure.

### 2. execution
Run the script from the project root:
```bash
uv run scripts/discovery/inspect_hf_dataset.py > data/discovery/schema_report.txt
```

### 3. verification
Manually review `data/discovery/schema_report.txt`.
- **Check**: Do column names match `CaseAdapter` expectations?
- **Check**: Are file paths strings or objects?
- **Check**: Are required fields (DWI, ADC) actually present?

### 4. remediation
If the report contradicts the code/specs:
1.  Update the spec (`docs/specs/`) to reflect reality.
2.  Update the code (`src/.../adapter.py`) to handle the actual schema.
3.  Add a regression test if the edge case is complex.

## git configuration
Ensure `.gitignore` includes:
```gitignore
data/isles24/
data/discovery/
```
