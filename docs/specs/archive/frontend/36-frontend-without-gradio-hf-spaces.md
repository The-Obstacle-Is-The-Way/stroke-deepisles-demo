# Spec 36: React Frontend + FastAPI Backend for HuggingFace Spaces

**Status**: APPROVED PLAN
**Date**: 2025-12-11
**Goal**: Replace Gradio with React frontend for NiiVue, FastAPI backend for DeepISLES

**UPDATE (2025-12-12):** See `NEXT-CONCERNS.md` for latest architecture fixes regarding config consolidation (BUG-009) and dependency reproducibility (BUG-012). The env var `FRONTEND_ORIGIN` is now `STROKE_DEMO_FRONTEND_ORIGINS`.

---

## Security Note: CVE-2025-55182 Does NOT Affect This App

**CVE-2025-55182 (React2Shell)** is a critical RCE vulnerability disclosed December 3, 2025.

| What | Status |
|------|--------|
| **React 19.x with RSC** | VULNERABLE if using Server Components |
| **React 19.x client-only** | SAFE - no Server Components = no vulnerability |
| **React 18.x** | NOT AFFECTED - no Server Components |

**We use React 19.2.0** which is **safe for our use case** because:
- CVE-2025-55182 only affects React Server Components (RSC)
- Our app is **client-only** (Static Space = no server-side rendering)
- We do not use React Server Components
- The vulnerability requires SSR/RSC to be exploitable

Sources:
- [React Security Advisory](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components)
- [Wiz Analysis](https://www.wiz.io/blog/critical-vulnerability-in-react-cve-2025-55182)

---

## The Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Frontend Framework** | React | 19.2.0 | UI components (client-only, see security note) |
| **Type Safety** | TypeScript | 5.9.3 | Type checking |
| **Build Tool** | Vite | 7.2.4 | Fast builds, HMR |
| **CSS Framework** | Tailwind CSS | 4.1.17 | Utility-first styling |
| **3D Viewer** | @niivue/niivue | 0.65.0 | WebGL2 NIfTI viewer |
| **Testing** | Vitest + Playwright | 4.0.15 / 1.57.0 | Unit, integration, E2E tests |
| **Backend Framework** | FastAPI | 0.124.2 | Python REST API |
| **ML Pipeline** | DeepISLES | existing | Stroke segmentation |

---

## Architecture: Two HuggingFace Spaces

You **need both** because:
- **Static Space** = JavaScript only (React, NiiVue) - cannot run Python
- **Docker Space** = Python runtime (FastAPI, DeepISLES, PyTorch)

```
┌─────────────────────────────────────┐
│  HuggingFace Static Space           │
│  stroke-viewer-frontend             │
│                                     │
│  React 19 + TypeScript + Tailwind   │
│  @niivue/niivue for 3D viewing      │
│                                     │
│  Serves: index.html, JS, CSS        │
│  Always on, never sleeps            │
└──────────────┬──────────────────────┘
               │ HTTPS API calls
               ▼
┌─────────────────────────────────────┐
│  HuggingFace Docker Space           │
│  stroke-viewer-api                  │
│                                     │
│  FastAPI + DeepISLES + PyTorch      │
│                                     │
│  Endpoints:                         │
│  - GET  /api/cases                  │
│  - POST /api/segment                │
│  - GET  /files/{run_id}/{case}/...  │
│                                     │
│  Sleeps after 48h inactivity        │
└─────────────────────────────────────┘
```

---

## Project Structure

This is an **existing monorepo** (`stroke-deepisles-demo`), NOT a new project. The frontend is
added alongside the existing Python package. The "backend" is the existing `src/stroke_deepisles_demo/`
package with a new `api/` submodule.

```
stroke-deepisles-demo/           # EXISTING monorepo
├── frontend/                    # NEW: React + NiiVue (Static Space)
│   ├── src/
│   │   ├── components/
│   │   │   ├── NiiVueViewer.tsx
│   │   │   ├── CaseSelector.tsx
│   │   │   ├── MetricsPanel.tsx
│   │   │   └── Layout.tsx
│   │   ├── hooks/
│   │   │   └── useSegmentation.ts
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── e2e/                     # Playwright E2E tests
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   ├── playwright.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── README.md                # HF Spaces YAML config
│
├── src/stroke_deepisles_demo/   # EXISTING Python package (Docker Space)
│   ├── api/                     # NEW: FastAPI REST API submodule
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── routes.py            # API endpoints
│   │   └── schemas.py           # Pydantic models
│   ├── core/                    # Config, logging (existing)
│   ├── data/                    # Data adapters (existing)
│   ├── inference/               # DeepISLES integration (existing)
│   ├── ui/                      # Gradio UI (being replaced)
│   ├── pipeline.py              # ML pipeline (existing)
│   └── metrics.py               # Metrics computation (existing)
│
├── tests/
│   ├── api/                     # NEW: API endpoint tests
│   │   ├── __init__.py
│   │   └── test_endpoints.py
│   └── ...                      # Existing tests
│
├── Dockerfile                   # Docker for HF Spaces (existing)
├── pyproject.toml               # Python package config (existing)
└── README.md
```

**Key difference from a greenfield project:** We're adding `frontend/` and `src/stroke_deepisles_demo/api/`
to an existing codebase, NOT creating separate `frontend/` and `backend/` directories.

---

## Frontend Implementation

### package.json

```json
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "@niivue/niivue": "^0.65.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.57.0",
    "@tailwindcss/vite": "^4.1.17",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.3.0",
    "@vitejs/plugin-react": "^5.1.1",
    "@vitest/coverage-v8": "^4.0.15",
    "eslint": "^9.39.1",
    "tailwindcss": "^4.1.17",
    "typescript": "~5.9.3",
    "vite": "^7.2.4",
    "vitest": "^4.0.15"
  }
}
```

**Why these versions:**
- `react` / `react-dom` **19.2.0**: Latest React 19 - client-only so CVE-2025-55182 doesn't apply
- `@niivue/niivue` **0.65.0**: Latest stable (Dec 2025)
- `vite` **7.2.4**: Latest stable v7
- `vitest` **4.0.15**: Fast unit testing with React Testing Library
- `@playwright/test` **1.57.0**: E2E browser testing
- `tailwindcss` **4.1.17**: Latest stable v4
- `typescript` **5.9.3**: Latest stable
- ESLint included for code quality in CI

### vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: 'dist',
  },
})
```

### TypeScript Configuration (Vite 7 Project References Pattern)

Vite 7 uses a project references pattern for better separation of app, test, and build configs:

**tsconfig.json** (root - references only):
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" },
    { "path": "./tsconfig.test.json" }
  ]
}
```

**tsconfig.app.json** (application code):
```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "types": ["vite/client"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"],
  "exclude": ["src/test", "src/mocks", "src/**/*.test.tsx", "src/**/*.test.ts"]
}
```

### src/index.css

```css
@import "tailwindcss";
```

### src/main.tsx

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

### src/App.tsx

```tsx
import { useState } from 'react'
import { Layout } from './components/Layout'
import { CaseSelector } from './components/CaseSelector'
import { NiiVueViewer } from './components/NiiVueViewer'
import { MetricsPanel } from './components/MetricsPanel'
import { useSegmentation } from './hooks/useSegmentation'

export default function App() {
  const [selectedCase, setSelectedCase] = useState<string | null>(null)
  const { result, isLoading, error, runSegmentation } = useSegmentation()

  const handleRunSegmentation = async () => {
    if (selectedCase) {
      await runSegmentation(selectedCase)
    }
  }

  return (
    <Layout>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel: Controls */}
        <div className="space-y-4">
          <CaseSelector
            selectedCase={selectedCase}
            onSelectCase={setSelectedCase}
          />
          <button
            onClick={handleRunSegmentation}
            disabled={!selectedCase || isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400
                       text-white font-medium py-3 px-4 rounded-lg transition"
          >
            {isLoading ? 'Processing...' : 'Run Segmentation'}
          </button>
          {error && (
            <div className="bg-red-100 text-red-700 p-3 rounded-lg">
              {error}
            </div>
          )}
          {result && <MetricsPanel metrics={result.metrics} />}
        </div>

        {/* Right Panel: Viewer */}
        <div className="lg:col-span-2">
          {result ? (
            <NiiVueViewer
              backgroundUrl={result.dwiUrl}
              overlayUrl={result.predictionUrl}
            />
          ) : (
            <div className="bg-gray-900 rounded-lg h-[500px] flex items-center justify-center">
              <p className="text-gray-400">
                Select a case and run segmentation to view results
              </p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
```

### src/components/Layout.tsx

```tsx
import { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 py-4">
        <div className="container mx-auto px-4">
          <h1 className="text-2xl font-bold">Stroke Lesion Segmentation</h1>
          <p className="text-gray-400 text-sm mt-1">
            DeepISLES segmentation on ISLES24 dataset
          </p>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  )
}
```

### src/components/NiiVueViewer.tsx

```tsx
import { useRef, useEffect } from 'react'
import { Niivue } from '@niivue/niivue'

interface NiiVueViewerProps {
  backgroundUrl: string
  overlayUrl?: string
}

export function NiiVueViewer({ backgroundUrl, overlayUrl }: NiiVueViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const nvRef = useRef<Niivue | null>(null)

  useEffect(() => {
    if (!canvasRef.current) return

    // Only instantiate NiiVue once; reuse for volume reloads
    let nv = nvRef.current
    if (!nv) {
      nv = new Niivue({
        backColor: [0.05, 0.05, 0.05, 1],
        show3Dcrosshair: true,
        crosshairColor: [1, 0, 0, 0.5],
      })
      nv.attachToCanvas(canvasRef.current)
      nvRef.current = nv
    }

    // Build volumes array - always reload when URLs change
    const volumes: Array<{ url: string; colormap: string; opacity: number }> = [
      { url: backgroundUrl, colormap: 'gray', opacity: 1 },
    ]

    if (overlayUrl) {
      volumes.push({
        url: overlayUrl,
        colormap: 'red',
        opacity: 0.5,
      })
    }

    // Load volumes (async but we don't await - just fire off)
    void nv.loadVolumes(volumes)

    // Cleanup on unmount - CRITICAL: Release WebGL context
    // Browsers limit WebGL contexts (~16 in Chrome). Without cleanup,
    // navigating between results will exhaust contexts and break the viewer.
    return () => {
      if (nvRef.current) {
        // Capture gl BEFORE cleanup (cleanup may null internal state)
        const gl = nvRef.current.gl
        try {
          // NiiVue's cleanup() releases event listeners and observers
          // See: https://niivue.github.io/niivue/devdocs/classes/Niivue.html#cleanup
          nvRef.current.cleanup()
          // Force WebGL context loss to free GPU memory immediately
          if (gl) {
            const ext = gl.getExtension('WEBGL_lose_context')
            ext?.loseContext()
          }
        } catch {
          // Ignore cleanup errors
        }
        nvRef.current = null
      }
    }
  }, [backgroundUrl, overlayUrl])

  return (
    <div className="bg-gray-900 rounded-lg p-2">
      <canvas
        ref={canvasRef}
        className="w-full h-[500px] rounded"
      />
      <div className="flex gap-4 mt-2 text-xs text-gray-400">
        <span>Scroll: Navigate slices</span>
        <span>Drag: Adjust contrast</span>
        <span>Right-click: Pan</span>
      </div>
    </div>
  )
}
```

### src/components/CaseSelector.tsx

```tsx
import { useEffect, useState } from 'react'
import { apiClient } from '../api/client'

interface CaseSelectorProps {
  selectedCase: string | null
  onSelectCase: (caseId: string) => void
}

export function CaseSelector({ selectedCase, onSelectCase }: CaseSelectorProps) {
  const [cases, setCases] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await apiClient.getCases()
        setCases(data.cases)
      } catch (err) {
        setError('Failed to load cases')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchCases()
  }, [])

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <p className="text-gray-400">Loading cases...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900 rounded-lg p-4">
        <p className="text-red-300">{error}</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <label className="block text-sm font-medium mb-2">
        Select Case
      </label>
      <select
        value={selectedCase || ''}
        onChange={(e) => onSelectCase(e.target.value)}
        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2
                   text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        <option value="">Choose a case...</option>
        {cases.map((caseId) => (
          <option key={caseId} value={caseId}>
            {caseId}
          </option>
        ))}
      </select>
    </div>
  )
}
```

### src/components/MetricsPanel.tsx

```tsx
interface Metrics {
  caseId: string
  diceScore: number | null
  volumeMl: number | null
  elapsedSeconds: number
}

interface MetricsPanelProps {
  metrics: Metrics
}

export function MetricsPanel({ metrics }: MetricsPanelProps) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-3">
      <h3 className="font-medium text-lg">Results</h3>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-400">Case:</span>
          <span className="ml-2 font-mono">{metrics.caseId}</span>
        </div>

        {metrics.diceScore !== null && (
          <div>
            <span className="text-gray-400">Dice Score:</span>
            <span className="ml-2 font-mono text-green-400">
              {metrics.diceScore.toFixed(3)}
            </span>
          </div>
        )}

        {metrics.volumeMl !== null && (
          <div>
            <span className="text-gray-400">Volume:</span>
            <span className="ml-2 font-mono">{metrics.volumeMl.toFixed(2)} mL</span>
          </div>
        )}

        <div>
          <span className="text-gray-400">Time:</span>
          <span className="ml-2 font-mono">{metrics.elapsedSeconds.toFixed(1)}s</span>
        </div>
      </div>
    </div>
  )
}
```

### src/api/client.ts

```typescript
// API base URL - configure via environment variable
const API_BASE = import.meta.env.VITE_API_URL || 'https://your-backend.hf.space'

interface CasesResponse {
  cases: string[]
}

interface SegmentResponse {
  caseId: string
  diceScore: number | null
  volumeMl: number | null
  elapsedSeconds: number
  dwiUrl: string
  predictionUrl: string
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async getCases(): Promise<CasesResponse> {
    const response = await fetch(`${this.baseUrl}/api/cases`)
    if (!response.ok) {
      throw new Error(`Failed to fetch cases: ${response.statusText}`)
    }
    return response.json()
  }

  async runSegmentation(caseId: string, fastMode = true): Promise<SegmentResponse> {
    const response = await fetch(`${this.baseUrl}/api/segment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        case_id: caseId,
        fast_mode: fastMode,
      }),
    })
    if (!response.ok) {
      throw new Error(`Segmentation failed: ${response.statusText}`)
    }
    return response.json()
  }
}

export const apiClient = new ApiClient(API_BASE)
```

### src/hooks/useSegmentation.ts

```typescript
import { useState, useCallback } from 'react'
import { apiClient } from '../api/client'

interface SegmentationResult {
  dwiUrl: string
  predictionUrl: string
  metrics: {
    caseId: string
    diceScore: number | null
    volumeMl: number | null
    elapsedSeconds: number
  }
}

export function useSegmentation() {
  const [result, setResult] = useState<SegmentationResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runSegmentation = useCallback(async (caseId: string) => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await apiClient.runSegmentation(caseId)
      setResult({
        dwiUrl: data.dwiUrl,
        predictionUrl: data.predictionUrl,
        metrics: {
          caseId: data.caseId,
          diceScore: data.diceScore,
          volumeMl: data.volumeMl,
          elapsedSeconds: data.elapsedSeconds,
        },
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setResult(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return { result, isLoading, error, runSegmentation }
}
```

### src/types/index.ts

```typescript
export interface Case {
  id: string
  name: string
}

export interface Metrics {
  caseId: string
  diceScore: number | null
  volumeMl: number | null
  elapsedSeconds: number
}

export interface SegmentationResult {
  dwiUrl: string
  predictionUrl: string
  metrics: Metrics
}
```

### index.html

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Stroke Lesion Segmentation</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### frontend/README.md (HuggingFace Spaces Config)

```markdown
---
title: Stroke Lesion Viewer
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: static
app_file: dist/index.html
app_build_command: npm run build
# CRITICAL: Vite 7 requires Node.js >= 20. HF Spaces defaults to Node 18.
# Without this, the build will fail or produce warnings.
nodejs_version: "20"
pinned: false
---

# Stroke Lesion Segmentation Viewer

Interactive 3D viewer for stroke lesion segmentation results using NiiVue.

Built with React, TypeScript, Tailwind CSS, and Vite.
```

---

## Backend Implementation

The backend is the **existing** `src/stroke_deepisles_demo/` Python package. We add a new
`api/` submodule for FastAPI endpoints. This keeps all Python code in one package with
proper imports (e.g., `from stroke_deepisles_demo.api.routes import router`).

### pyproject.toml (additions)

Add these dependencies to the existing `pyproject.toml`:

```toml
[project.optional-dependencies]
api = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
]
```

### src/stroke_deepisles_demo/api/__init__.py

```python
"""FastAPI REST API for stroke segmentation."""

from stroke_deepisles_demo.api.main import app

__all__ = ["app"]
```

### src/stroke_deepisles_demo/api/main.py

```python
"""FastAPI application for stroke segmentation API."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from stroke_deepisles_demo.api.routes import router

app = FastAPI(
    title="Stroke Segmentation API",
    description="DeepISLES stroke lesion segmentation",
    version="1.0.0",
)

# CORS configuration
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "")
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative local port
]
if FRONTEND_ORIGIN:
    CORS_ORIGINS.append(FRONTEND_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # Match HF Spaces URLs in both formats (direct and proxy)
    allow_origin_regex=r"https://.*stroke-viewer-frontend.*\\.hf\\.space",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# Static files for NIfTI results (only mount if directory exists)
RESULTS_DIR = "/tmp/stroke-results"
if os.path.exists(RESULTS_DIR):
    app.mount("/files", StaticFiles(directory=RESULTS_DIR), name="files")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "stroke-segmentation-api"}
```

### src/stroke_deepisles_demo/api/routes.py

```python
"""API route handlers."""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from stroke_deepisles_demo.api.schemas import CasesResponse, SegmentRequest, SegmentResponse
from stroke_deepisles_demo.data import list_case_ids
from stroke_deepisles_demo.pipeline import run_pipeline_on_case
from stroke_deepisles_demo.metrics import compute_volume_ml

router = APIRouter()

# Base directory for results
RESULTS_BASE = Path("/tmp/stroke-results")


def get_backend_base_url(request: Request) -> str:
    """Get the backend's public URL for building absolute file URLs.

    Priority:
    1. BACKEND_PUBLIC_URL env var (for production HF Spaces)
    2. Request's base URL (for local development)
    """
    env_url = os.environ.get("BACKEND_PUBLIC_URL", "").rstrip("/")
    if env_url:
        return env_url
    return str(request.base_url).rstrip("/")


@router.get("/cases", response_model=CasesResponse)
async def get_cases():
    """List available cases from dataset."""
    try:
        cases = list_case_ids()
        return CasesResponse(cases=cases)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/segment", response_model=SegmentResponse)
async def run_segmentation(request: Request, body: SegmentRequest):
    """Run DeepISLES segmentation on a case."""
    try:
        # Generate unique run ID to avoid conflicts
        run_id = str(uuid.uuid4())[:8]
        output_dir = RESULTS_BASE / run_id

        result = run_pipeline_on_case(
            body.case_id,
            output_dir=output_dir,
            fast=body.fast_mode,
            compute_dice=True,
            cleanup_staging=True,
        )

        # Compute volume
        volume_ml = None
        try:
            volume_ml = round(compute_volume_ml(result.prediction_mask, threshold=0.5), 2)
        except Exception:
            pass

        # Build absolute file URLs
        backend_url = get_backend_base_url(request)
        dwi_filename = result.input_files["dwi"].name
        pred_filename = result.prediction_mask.name

        file_path_prefix = f"/files/{run_id}/{result.case_id}"

        return SegmentResponse(
            caseId=result.case_id,
            diceScore=result.dice_score,
            volumeMl=volume_ml,
            elapsedSeconds=round(result.elapsed_seconds, 2),
            dwiUrl=f"{backend_url}{file_path_prefix}/{dwi_filename}",
            predictionUrl=f"{backend_url}{file_path_prefix}/{pred_filename}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### src/stroke_deepisles_demo/api/schemas.py

```python
"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel


class CasesResponse(BaseModel):
    """Response for GET /api/cases."""

    cases: list[str]


class SegmentRequest(BaseModel):
    """Request body for POST /api/segment."""

    case_id: str
    fast_mode: bool = True


class SegmentResponse(BaseModel):
    """Response for POST /api/segment."""

    caseId: str
    diceScore: float | None
    volumeMl: float | None
    elapsedSeconds: float
    dwiUrl: str
    predictionUrl: str
```

### Dockerfile (update existing)

The existing `Dockerfile` at project root needs to be updated for the API:

```dockerfile
# CRITICAL: Must use isleschallenge/deepisles base image
# This image contains:
# - PyTorch with CUDA support
# - Pre-installed DeepISLES model weights (~18GB)
# - All medical imaging dependencies (nibabel, nnunet, etc.)
FROM isleschallenge/deepisles:latest

WORKDIR /app

# Copy the project
COPY pyproject.toml .
COPY src/ src/
COPY README.md .

# Install the package with API dependencies
RUN pip install --no-cache-dir -e ".[api]"

# Create results directory (used by StaticFiles mount)
RUN mkdir -p /tmp/stroke-results

# Environment variables for HuggingFace Spaces
ENV HF_SPACES=1
ENV DEEPISLES_DIRECT_INVOCATION=1

# Expose port (HF Spaces expects 7860)
EXPOSE 7860

# Run FastAPI (note: module path is stroke_deepisles_demo.api.main:app)
CMD ["uvicorn", "stroke_deepisles_demo.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

**CRITICAL: GPU Required**

DeepISLES requires GPU acceleration. HuggingFace Spaces FREE tier (`cpu-basic`) will NOT work.

| Tier | GPU | Will Work? |
|------|-----|------------|
| `cpu-basic` (free) | None | ❌ No |
| `t4-small` | NVIDIA T4 (16GB) | ✅ Yes |
| `t4-medium` | NVIDIA T4 (16GB) | ✅ Yes |
| `a10g-small` | NVIDIA A10G (24GB) | ✅ Yes |

When creating the HF Space, select **T4-small** or higher.

**Note:** The Dockerfile copies the full project because `requirements.txt` has:
```
stroke-deepisles-demo @ file:.
```
This PEP 508 local path reference requires the package source to be present.

### backend/README.md (HuggingFace Spaces Config)

```markdown
---
title: Stroke Segmentation API
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Stroke Segmentation API

FastAPI backend running DeepISLES stroke lesion segmentation.

## Endpoints

- `GET /api/cases` - List available cases
- `POST /api/segment` - Run segmentation
- `GET /files/{filename}` - Download result files
```

---

## Setup Commands

### Frontend (Local Development)

```bash
cd frontend

# Install dependencies (already configured in package.json)
npm install

# Run dev server
npm run dev
# Opens http://localhost:5173

# Run tests
npm test                  # Unit tests with Vitest
npm run test:e2e          # E2E tests with Playwright
npm run test:coverage     # Coverage report
```

### Backend (Local Development)

```bash
# From project root (stroke-deepisles-demo/)

# Install with API dependencies
pip install -e ".[api]"

# Run server
uvicorn stroke_deepisles_demo.api.main:app --reload --port 7860
# Opens http://localhost:7860

# Run API tests
pytest tests/api/ -v
```

### Deploy to HuggingFace

```bash
# Frontend (Static Space) - deploy from frontend/ directory
cd frontend
npm run build
huggingface-cli repo create stroke-viewer-frontend --type space --space-sdk static
huggingface-cli upload stroke-viewer-frontend ./dist . --repo-type space

# Backend (Docker Space) - deploy from project root
# The Dockerfile at project root builds the full package including API
huggingface-cli repo create stroke-viewer-api --type space --space-sdk docker
huggingface-cli upload stroke-viewer-api . . --repo-type space
```

---

## Environment Variables

### Frontend (.env)

```env
VITE_API_URL=https://your-username-stroke-viewer-api.hf.space
```

### Backend

No additional env vars needed - uses existing stroke-deepisles-demo configuration.

---

## Key Differences from Gradio

| What | Gradio (broken) | This Stack |
|------|-----------------|------------|
| NiiVue JavaScript | Blocked by innerHTML | Full execution ✓ |
| WebGL2 context | Frozen during hydration | Works normally ✓ |
| Bundle size | ~2MB Gradio overhead | ~200KB total |
| Cold start | Python + Gradio init | Instant (static) |
| Customization | Limited to Gradio components | Full React control |

---

## Next Steps

1. ✅ Create `frontend/` directory with React + NiiVue (DONE - PR #32 merged)
2. ✅ Create `src/stroke_deepisles_demo/api/` submodule with FastAPI (DONE)
3. ✅ Create `tests/api/` with endpoint tests (DONE - 8 tests passing)
4. Test locally: `npm run dev` + `uvicorn stroke_deepisles_demo.api.main:app`
5. Create HuggingFace Spaces (one Static, one Docker)
6. Deploy and test

---

## Dependencies Summary (Verified Dec 11, 2025)

**Frontend (npm) - ACTUAL VERSIONS (from package.json):**
| Package | Version | Notes |
|---------|---------|-------|
| react | ^19.2.0 | React 19 client-only (safe from CVE-2025-55182) |
| react-dom | ^19.2.0 | Must match react version |
| @niivue/niivue | ^0.65.0 | Latest stable |
| typescript | ~5.9.3 | Latest 5.9.x |
| vite | ^7.2.4 | Latest v7 |
| tailwindcss | ^4.1.17 | Latest v4 |
| @tailwindcss/vite | ^4.1.17 | Must match tailwindcss |
| @vitejs/plugin-react | ^5.1.1 | Latest stable |

**Backend (pip) - VERSIONS (from pyproject.toml):**
| Package | Version | Notes |
|---------|---------|-------|
| fastapi | >=0.115.0 | Latest compatible |
| uvicorn[standard] | >=0.32.0 | Latest stable |
| pydantic | (bundled) | Included with FastAPI |

**Node.js:** >= 20.0.0 (required for Vite 7)
**Python:** >= 3.11 (recommended for FastAPI)
