# Next Concerns - Critical Architecture Debt

**Status:** VALIDATED - All claims verified from first principles
**Priority:** P0/P1 - Production reproducibility and config integrity at risk

---

## PART 1: CONFIG DRIFT (BUG-009) - RESOLVED

### Status
- **Consolidated:** `api/config.py` deleted.
- **SSOT:** `core/config.py` now holds all API settings.
- **Env Vars:** `Dockerfile` updated to use `STROKE_DEMO_*` prefix.
- **Validation:** Tests pass, env var overrides work.

---

## PART 2: DEPENDENCY PINNING (BUG-012) - RESOLVED

### Status
- **Base Image:** Pinned to `sha256:848c9eceb67dbc585bcb37f093389d142caeaa98878bd31039af04ef297a5af4`.
- **Lock File:** Dockerfile now uses `uv sync --frozen` to respect `uv.lock`.
- **Path:** Dockerfile adds `.venv/bin` to `PATH` for correct execution.
- **Dependency Migration:** Migrated from hard-forked `datasets` to maintained `neuroimaging-go-brrrr` extension (v0.2.1) + standard `datasets` library. Validated end-to-end in Docker.
- **Validation:** Docker build succeeds, runtime verifies settings load and modules importable.

---

## PART 3: FRONTEND CONFIG - NO ACTION NEEDED

### Status
- Keeping current build-time `.env.production` approach.
- No immediate need for runtime variables via `window.huggingface.variables`.

---

**Validated:** 2025-12-12
**Status:** COMPLETED
