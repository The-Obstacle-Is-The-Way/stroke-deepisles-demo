# Bug Spec: HuggingFace Spaces Dataset Loading Loop

**Status:** Open
**Priority:** P0 (Blocks deployment)
**Branch:** `debug/hf-spaces-dataset-error`
**Date:** 2025-12-08

## Observed Behavior

Container enters infinite restart loop:
1. Application starts successfully (`Running on local URL: http://0.0.0.0:7860`)
2. Dataset download completes (`Downloading data: 100%|██████████| 149/149`)
3. "Generating train split" begins processing
4. **Container restarts** (new `Application Startup` timestamp)
5. Cycle repeats indefinitely

The "Select Case" dropdown **never** populates. Users see "Preparing Space" spinner forever.

## Environment

- **Space:** `VibecoderMcSwaggins/stroke-deepisles-demo`
- **Hardware:** T4-small GPU
- **Base Image:** `isleschallenge/deepisles:latest`
- **Dataset:** `hugging-science/isles24-stroke` (149 NIfTI files, ~2-5MB each)
- **Commit:** `a2223b1`

## Timeline from Logs

```text
16:43:33 - Application Startup
16:43:33 - Initializing dataset...
16:43:33 - Downloading data: 0%
16:48:10 - Downloading data: 100% (149/149) [~5 min]
16:48:10 - Generating train split: starts
16:56:53 - Application Startup (RESTART - lost all progress)
16:56:53 - Downloading data: 0% (starts over)
```

## Hypotheses

### H1: Memory OOM during train split generation
- Processing 149 NIfTI files into HF Dataset format
- Each file loaded into memory for processing
- T4-small may have limited RAM
- **Evidence:** Restart happens during "Generating train split" phase

### H2: Disk space exhaustion
- HF Spaces ephemeral storage limit (~50GB based on org space error)
- DeepISLES base image is large
- Dataset download + cache + processing temps
- **Evidence:** Org space explicitly failed with "storage limit exceeded (50G)"

### H3: Gradio demo.load() timeout
- `demo.load()` has internal timeout?
- 7+ minutes for dataset loading exceeds limit?
- **Evidence:** UI shows "Preparing Space" during load

### H4: HF Spaces health check failure
- Even though port 7860 is bound, health check may require response
- Long-running `demo.load()` blocks event loop?
- **Evidence:** Container restarts after ~13 min total

### H5: Exception swallowed during train split
- Our try/except returns `gr.Dropdown(info=f"Error: {e}")`
- But Gradio shows generic "Error" not our message
- Something crashes before our handler

## Code Under Suspicion

### `src/stroke_deepisles_demo/ui/app.py:34-56`
```python
def initialize_case_selector() -> gr.Dropdown:
    try:
        logger.info("Initializing dataset for case selector...")
        case_ids = list_case_ids()  # <-- This triggers full dataset load

        if not case_ids:
            return gr.Dropdown(choices=[], info="No cases found in dataset.")

        return gr.Dropdown(
            choices=case_ids,
            value=case_ids[0],
            info="Choose a case from isles24-stroke dataset",
            interactive=True,
        )
    except Exception as e:
        logger.exception("Failed to initialize dataset")
        return gr.Dropdown(choices=[], info=f"Error loading data: {e!s}")
```

### `src/stroke_deepisles_demo/data/loader.py`
- `list_case_ids()` calls `load_isles_dataset()`
- `load_isles_dataset()` calls HF `load_dataset()` (non-streaming)
- Full dataset downloaded and processed into memory

## Potential Fixes

### Fix 1: Streaming Mode (Recommended)
```python
# Instead of:
ds = load_dataset("hugging-science/isles24-stroke")

# Use streaming:
ds = load_dataset("hugging-science/isles24-stroke", streaming=True)
case_ids = [ex["case_id"] for ex in ds]  # Iterate without full load
```
- **Pros:** Zero disk usage, immediate start
- **Cons:** Can't random access, must iterate

### Fix 2: Lazy case ID loading
- Only load case IDs, not full dataset
- Use HF Hub API to list files without downloading

### Fix 3: Pre-computed case ID list
- Hardcode or cache the 149 case IDs
- Skip dataset enumeration entirely for dropdown

### Fix 4: Persistent Storage
- Enable HF Spaces Persistent Storage add-on
- Cache survives restarts
- **Cons:** Costs money, doesn't fix root cause

### Fix 5: Background thread with timeout
- Run dataset load in background thread
- Show "Loading..." in dropdown immediately
- Update dropdown when ready (if ever)

## Investigation Needed

1. **Get actual error:** What exception/signal causes restart?
   - Need HF Spaces runtime logs (not just container logs)
   - Check for OOM killer, SIGKILL, etc.

2. **Measure resource usage:**
   - Disk usage during download/processing
   - Memory usage during train split generation

3. **Test streaming mode locally:**
   - Does `streaming=True` work with our dataset?
   - Can we still get case IDs?

4. **Check Gradio demo.load() behavior:**
   - Is there a timeout?
   - Does long-running load block health checks?

## Reproduction Steps

1. Go to [the demo space](https://huggingface.co/spaces/VibecoderMcSwaggins/stroke-deepisles-demo)
2. Open Logs tab
3. Watch download complete (5 min)
4. Watch "Generating train split" start
5. Observe container restart (~7-13 min mark)
6. See download start over from 0%

## Related Issues

- Org space (`hugging-science/stroke-deepisles-demo`) failed with explicit "storage limit exceeded (50G)"
- This suggests disk space IS a factor
- Personal space may have same limit but hits it slower

## Next Steps

1. [ ] Get deep analysis from senior reviewer / external agent
2. [ ] Test streaming mode locally
3. [ ] Add resource monitoring/logging
4. [ ] Consider pre-computed case ID approach as quick fix
