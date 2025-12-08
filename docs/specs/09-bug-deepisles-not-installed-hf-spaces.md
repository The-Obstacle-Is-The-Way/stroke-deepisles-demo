# Bug Spec: DeepISLES Path Conflict in Docker Build

**Status:** Root Cause Found → Fix Ready
**Priority:** P0 (Blocks inference)
**Branch:** `fix/deepisles-docker-path`
**Date:** 2025-12-08

## Executive Summary

Our Dockerfile was **overwriting DeepISLES modules** by copying our app to `/app/src/`, which is where the base image stores DeepISLES code. The fix is to install our app at `/home/user/demo` instead.

## Root Cause

The `isleschallenge/deepisles:latest` Docker image has this structure:
```text
/app/
├── main.py
├── requirements.txt
├── src/                    ← DeepISLES Python modules
│   └── isles22_ensemble.py
└── weights/                ← Model weights (~GB)
```

Our original Dockerfile:
```dockerfile
FROM isleschallenge/deepisles:latest
WORKDIR /app
COPY src/ /app/src/         ← OVERWRITES DeepISLES modules!
```

This replaced `/app/src/isles22_ensemble.py` (DeepISLES) with `/app/src/stroke_deepisles_demo/` (our app).

## The Fix

1. **Changed app directory** from `/app` to `/home/user/demo`
2. **Added `DEEPISLES_PATH=/app`** environment variable
3. **Updated `direct.py`** to check `DEEPISLES_PATH` first

### Dockerfile Changes
```dockerfile
# Before: WORKDIR /app
# After:
WORKDIR /home/user/demo

# Before: COPY src/ /app/src/
# After:
COPY src/ /home/user/demo/src/

# New:
ENV DEEPISLES_PATH=/app
```

### direct.py Changes
```python
def _get_deepisles_search_paths() -> list[str]:
    paths = []
    # Check environment variable first (set in Dockerfile)
    env_path = os.environ.get("DEEPISLES_PATH")
    if env_path:
        paths.append(env_path)
    # Add common installation locations
    paths.extend(["/app", "/DeepIsles", ...])
    return paths
```

## Investigation Process

1. Pulled `isleschallenge/deepisles:latest` locally
2. Inspected WORKDIR: `/app`
3. Listed `/app` contents: found `src/`, `weights/`, `main.py`
4. Realized our `COPY src/ /app/src/` was overwriting DeepISLES

## Files Changed

- `Dockerfile` - Use `/home/user/demo`, add `DEEPISLES_PATH`
- `src/stroke_deepisles_demo/inference/direct.py` - Dynamic search paths

## Testing

- All 125 unit tests pass
- Need to test on HF Spaces to verify inference works

## References

- [DeepISLES GitHub](https://github.com/ezequieldlrosa/DeepIsles)
- [Docker Hub Image](https://hub.docker.com/r/isleschallenge/deepisles)
- [HuggingFace Docker Spaces](https://huggingface.co/docs/hub/en/spaces-sdks-docker)

## Sources

- [Docker Blog: Build ML Apps with HuggingFace](https://www.docker.com/blog/build-machine-learning-apps-with-hugging-faces-docker-spaces/)
- [HuggingFace Docker Spaces Docs](https://huggingface.co/docs/hub/en/spaces-sdks-docker)
