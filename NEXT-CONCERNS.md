# Next Concerns - Critical Architecture Debt

**Status:** VALIDATED - All claims verified from first principles
**Priority:** P0/P1 - Production reproducibility and config integrity at risk

---

## PART 1: CONFIG DRIFT (BUG-009) - CRITICAL

### Current State: Two Parallel Config Systems

**System A: Pydantic Settings** (`core/config.py`)

```python
# Line 93
results_dir: Path = Path("./results")
```

- Uses `STROKE_DEMO_*` env prefix
- Supports `.env` file loading
- Used by: `inference/deepisles.py`, `ui/components.py`, `ui/app.py`

**System B: Module Constants** (`api/config.py`)

```python
# Line 10
RESULTS_DIR = Path("/tmp/stroke-results")
```

- Raw constants, no env var support
- Used by: `routes.py`, `files.py`, `main.py`, `job_store.py`

### The Problem

These define **DIFFERENT VALUES** for the same concept:

- `./results` vs `/tmp/stroke-results`

Production uses System B (API), but System A exists and could cause confusion.

### Env Var Fragmentation

| Where | Var Name | System |
|-------|----------|--------|
| Dockerfile:79 | `FRONTEND_ORIGIN` | Raw env var |
| Dockerfile:83 | `BACKEND_PUBLIC_URL` | Raw env var |
| core/config.py:68 | `STROKE_DEMO_*` | Pydantic Settings |

**These don't talk to each other.** The Dockerfile sets raw vars that Settings doesn't read.

### Recommended Fix

**Option B from audit: Pydantic Settings as SSOT**

1. Add API-relevant settings to `core/config.py`:
   - `results_dir` (already exists, fix default to `/tmp/stroke-results`)
   - `max_concurrent_jobs`
   - `frontend_origin`
   - `backend_public_url`

2. Delete or convert `api/config.py` to thin shim that imports from Settings

3. Update Dockerfile env vars to use `STROKE_DEMO_*` prefix

4. Update all API modules to import from `core/config.py`

---

## PART 2: DEPENDENCY PINNING (BUG-012) - CRITICAL

### Current State: Production Build is NOT Reproducible

**What we have:**

- `uv.lock` ✅ Committed and used by CI
- `requirements.txt` ⚠️ Has loose `>=` ranges
- Dockerfile uses `pip install -r requirements.txt` ❌ **IGNORES uv.lock**

**Evidence:**

```dockerfile
# Dockerfile:37 - IGNORES uv.lock!
RUN pip install --no-cache-dir -r requirements.txt
```

```txt
# requirements.txt - LOOSE PINS
fastapi>=0.115.0
pydantic>=2.5.0
uvicorn[standard]>=0.32.0
```

### Base Image Unpinned

```dockerfile
# Dockerfile:16 - NO SHA DIGEST
FROM isleschallenge/deepisles:latest
```

`:latest` can change anytime. A rebuild tomorrow could get different dependencies.

### The Problem

| Environment | Install Method | Reproducible? |
|-------------|----------------|---------------|
| CI | `uv sync` | ✅ Yes |
| Local dev | `uv sync` | ✅ Yes |
| **Production Docker** | `pip install -r requirements.txt` | ❌ **NO** |

### Recommended Fix

**Option A: Make Docker use uv.lock**

```dockerfile
# Install uv
RUN pip install uv

# Copy lock file
COPY uv.lock pyproject.toml ./

# Install from lock (frozen = fail if lock is stale)
RUN uv sync --frozen --no-dev
```

**Option B: Pin requirements.txt exactly**

```txt
# requirements.txt - EXACT PINS
fastapi==0.115.6
pydantic==2.10.3
uvicorn[standard]==0.32.1
```

**Either way: Pin the base image**

```dockerfile
# Get digest from: docker pull isleschallenge/deepisles:latest && docker images --digests
FROM isleschallenge/deepisles@sha256:<actual-digest>
```

---

## PART 3: FRONTEND CONFIG

### Current State

- `frontend/.env.production` hardcodes API URL at build time
- Works but not flexible for different deployments

### HF Static Spaces Alternative

HF exposes runtime variables via `window.huggingface.variables`. Currently unused.

### Recommendation

Keep current approach (build-time `.env.production`) unless multi-deployment flexibility needed.

---

## MIGRATION PLAN

### Phase 1: Config Consolidation (BUG-009)

1. Add to `core/config.py` Settings class:

   ```python
   # API settings
   results_dir: Path = Path("/tmp/stroke-results")  # Fix default
   max_concurrent_jobs: int = 10
   frontend_origins: list[str] = ["http://localhost:5173"]
   backend_public_url: str | None = None
   ```

2. Update Dockerfile env vars:

   ```dockerfile
   ENV STROKE_DEMO_FRONTEND_ORIGINS='["https://...hf.space"]'
   ENV STROKE_DEMO_BACKEND_PUBLIC_URL=https://...hf.space
   ```

3. Update imports in API modules:
   - `routes.py`, `files.py`, `main.py`, `job_store.py`
   - Change from `api.config` to `core.config.get_settings()`

4. Delete `api/config.py` or convert to compatibility shim

### Phase 2: Dependency Reproducibility (BUG-012)

1. Pin base image with SHA digest in Dockerfile

2. Choose ONE lock strategy:
   - **Recommended:** Make Dockerfile use `uv sync --frozen`
   - Alternative: Generate pinned requirements.txt from uv.lock

3. Update CI to use `--frozen` flag (fail if lock stale)

### Phase 3: Validation

1. Build Docker image locally
2. Verify all settings load correctly
3. Verify reproducible builds (rebuild should get same versions)

---

## SOURCES

- FastAPI Settings: https://fastapi.tiangolo.com/advanced/settings/
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- uv sync docs: https://docs.astral.sh/uv/concepts/projects/sync/
- Docker pinning: https://docs.docker.com/build/building/best-practices/
- 12-Factor Config: https://12factor.net/config

---

**Validated:** 2024-12-12
**Status:** Ready for implementation
