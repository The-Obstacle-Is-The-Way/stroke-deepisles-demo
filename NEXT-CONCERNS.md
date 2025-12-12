# Next Concerns - To Investigate

Deferred items from BUGS-AUDIT-2024-12-12.md that need deeper investigation.

---

## BUG-009: Results Directory Configuration Drift

**Priority:** P2 (Medium)

### Current State

Two files define where results go:
- `core/config.py:93` → `results_dir: Path = Path("./results")`
- `api/config.py:10` → `RESULTS_DIR = Path("/tmp/stroke-results")`

### Investigation Needed

1. **Does anything actually use `core/config.py`'s `results_dir`?**
   - Grep codebase for imports from `core/config`
   - If nothing uses it, delete the duplicate
   - If something uses it, consolidate to single source of truth

2. **Gold standard pattern:**
   ```python
   # api/config.py (SSOT)
   RESULTS_DIR = Path("/tmp/stroke-results")

   # core/config.py (if needed)
   from stroke_deepisles_demo.api.config import RESULTS_DIR
   ```

### Action

Run investigation, then either:
- Delete unused `core/config.py` results_dir, OR
- Make it import from `api/config.py`

---

## BUG-012: Loose Dependency Pinning

**Priority:** P3 (Low)

### Current State

- `pyproject.toml` uses `>=` ranges (e.g., `fastapi>=0.115.0`)
- `package.json` uses `^` ranges (e.g., `"react": "^19.2.0"`)

### Reality Check

Lock files exist and are committed:
- `uv.lock` → Backend installs are deterministic
- `package-lock.json` → Frontend installs are deterministic

**Builds ARE reproducible** if you use the lock files.

### Investigation Needed

1. Verify `uv.lock` is committed: `git ls-files uv.lock`
2. Verify Docker uses `uv sync` (respects lock) not `uv pip install` (ignores lock)
3. Verify CI uses lock files

### Action

If lock files are committed and used correctly:
- Close as "mitigated by lock files"
- Optionally add README note about reproducible builds

If lock files are NOT being used:
- Fix CI/Docker to use them
- Document requirement

---

**Created:** 2024-12-12
**Status:** Pending investigation
