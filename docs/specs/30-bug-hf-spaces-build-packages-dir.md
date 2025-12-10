# Spec #30: HF Spaces Build Error - Missing packages/ Directory

## Status: 🔴 P0 BLOCKER

## Issue
HuggingFace Spaces Docker build fails with:
```
ERROR: Invalid requirement: './packages/niivueviewer': Expected package name at the start of dependency specifier
    ./packages/niivueviewer
    ^ (from line 28 of requirements.txt)
Hint: It looks like a path. File './packages/niivueviewer' does not exist.
```

## Root Cause Analysis

### Timeline
1. PR #29 added `gradio_niivueviewer` custom component in `packages/niivueviewer/`
2. Added `./packages/niivueviewer` to `requirements.txt` line 28 for local installs
3. Dockerfile copies `requirements.txt` but NOT `packages/` directory
4. `pip install -r requirements.txt` fails because path doesn't exist

### Architecture Gap
```
Local Development:
  requirements.txt → ./packages/niivueviewer → ✅ EXISTS

HF Spaces Docker:
  COPY requirements.txt → Container
  pip install -r requirements.txt
  → ./packages/niivueviewer → ❌ NOT COPIED
```

## Solution Options

### Option A: Copy packages/ in Dockerfile (Recommended)
Add `COPY --chown=1000:1000 packages/ /home/user/demo/packages/` before pip install.

**Pros:**
- Simple fix
- Preserves local development workflow
- Editable install works correctly

**Cons:**
- Adds ~1.3MB to Docker image (compiled JS bundle)

### Option B: Build wheel and include in Docker
Pre-build wheel, copy to container, install from wheel file.

**Pros:**
- More "production" approach

**Cons:**
- More complex build process
- Need to manage wheel artifacts

### Option C: Separate requirements files
Create `requirements-docker.txt` without local path dependencies.

**Pros:**
- Clear separation of concerns

**Cons:**
- Duplicate maintenance
- Easy to drift out of sync

## Recommended Fix

**Option A** - Simple, maintainable, aligns with how local development works.

### Implementation

```dockerfile
# BEFORE pip install, add:
COPY --chown=1000:1000 packages/ /home/user/demo/packages/
```

### Full Dockerfile Change

```dockerfile
# Copy requirements first for better layer caching
COPY --chown=1000:1000 requirements.txt /home/user/demo/requirements.txt

# Copy custom component packages (required for pip install)
COPY --chown=1000:1000 packages/ /home/user/demo/packages/

# Install Python dependencies into SYSTEM Python
RUN pip install --no-cache-dir -r requirements.txt
```

## Test Plan

### Level 1: Local Docker Build
```bash
docker build -t stroke-demo-test .
docker run -p 7860:7860 stroke-demo-test
```

### Level 2: HF Spaces Deploy
Push to HF Spaces, verify build succeeds and app loads.

### Level 3: Functional Test
- Upload NIfTI files
- Run segmentation
- Verify NiiVue 3D viewer renders volumes

## Files to Modify
- `Dockerfile` - Add COPY for packages/ directory

## Risk Assessment
- **Low risk** - Additive change, doesn't modify existing code
- **Reversible** - Can easily remove if issues arise

## Acceptance Criteria
- [ ] HF Spaces build succeeds
- [ ] App loads without "Loading..." hang
- [ ] NiiVue viewer displays volumes correctly
