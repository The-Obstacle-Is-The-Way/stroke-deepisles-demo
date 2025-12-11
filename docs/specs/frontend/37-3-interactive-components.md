# Spec 37.3: Interactive Components

**Status**: READY FOR IMPLEMENTATION
**Phase**: 3 of 5
**Depends On**: Spec 37.2 (API Layer)
**Goal**: TDD implementation of CaseSelector and NiiVueViewer components

---

## Deliverables

By the end of this phase, you will have:

1. `CaseSelector` dropdown that fetches and displays cases
2. `NiiVueViewer` component for 3D medical image viewing
3. Loading and error states for both components
4. WebGL mocking for NiiVue tests

---

## Component 1: CaseSelector

### Test First

Create `src/components/__tests__/CaseSelector.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { server } from '../../mocks/server'
import { errorHandlers } from '../../mocks/handlers'
import { CaseSelector } from '../CaseSelector'

describe('CaseSelector', () => {
  const mockOnSelectCase = vi.fn()

  beforeEach(() => {
    mockOnSelectCase.mockClear()
  })

  it('shows loading state initially', () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('renders select after loading', async () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })
  })

  it('displays all cases as options', async () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    expect(screen.getByRole('option', { name: /sub-stroke0001/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /sub-stroke0002/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /sub-stroke0003/i })).toBeInTheDocument()
  })

  it('has placeholder option', async () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    expect(screen.getByRole('option', { name: /choose a case/i })).toBeInTheDocument()
  })

  it('calls onSelectCase when case selected', async () => {
    const user = userEvent.setup()

    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')

    expect(mockOnSelectCase).toHaveBeenCalledWith('sub-stroke0001')
  })

  it('shows selected case value', async () => {
    render(
      <CaseSelector
        selectedCase="sub-stroke0002"
        onSelectCase={mockOnSelectCase}
      />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toHaveValue('sub-stroke0002')
    })
  })

  it('shows error state on API failure', async () => {
    server.use(errorHandlers.casesServerError)

    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    })
  })

  it('applies correct styling', async () => {
    render(
      <CaseSelector selectedCase={null} onSelectCase={mockOnSelectCase} />
    )

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument()
    })

    const container = screen.getByRole('combobox').closest('div')
    expect(container).toHaveClass('bg-gray-800')
  })
})
```

### Implementation

Create `src/components/CaseSelector.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { apiClient } from '../api/client'

interface CaseSelectorProps {
  selectedCase: string | null
  onSelectCase: (caseId: string) => void
}

export function CaseSelector({ selectedCase, onSelectCase }: CaseSelectorProps) {
  const [cases, setCases] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await apiClient.getCases()
        setCases(data.cases)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error'
        setError(`Failed to load cases: ${message}`)
      } finally {
        setIsLoading(false)
      }
    }

    fetchCases()
  }, [])

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <p className="text-gray-400">Loading cases...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/50 rounded-lg p-4">
        <p className="text-red-300">{error}</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <label className="block text-sm font-medium mb-2">Select Case</label>
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

### Verify

```bash
npm test -- CaseSelector
# Expected: 9 tests passing
```

---

## Component 2: NiiVueViewer

### WebGL Mock Setup

Update `src/test/setup.ts` to add WebGL mocking:

```typescript
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, afterAll, vi } from 'vitest'
import { server } from '../mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

afterEach(() => {
  cleanup()
  server.resetHandlers()
})

afterAll(() => server.close())

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock WebGL2 context for NiiVue
const mockWebGL2Context = {
  canvas: null as HTMLCanvasElement | null,
  drawingBufferWidth: 640,
  drawingBufferHeight: 480,
  createShader: vi.fn(() => ({})),
  shaderSource: vi.fn(),
  compileShader: vi.fn(),
  getShaderParameter: vi.fn(() => true),
  createProgram: vi.fn(() => ({})),
  attachShader: vi.fn(),
  linkProgram: vi.fn(),
  getProgramParameter: vi.fn(() => true),
  useProgram: vi.fn(),
  getAttribLocation: vi.fn(() => 0),
  getUniformLocation: vi.fn(() => ({})),
  createBuffer: vi.fn(() => ({})),
  bindBuffer: vi.fn(),
  bufferData: vi.fn(),
  enableVertexAttribArray: vi.fn(),
  vertexAttribPointer: vi.fn(),
  createTexture: vi.fn(() => ({})),
  bindTexture: vi.fn(),
  texParameteri: vi.fn(),
  texImage2D: vi.fn(),
  activeTexture: vi.fn(),
  uniform1i: vi.fn(),
  uniform1f: vi.fn(),
  uniform2f: vi.fn(),
  uniform3f: vi.fn(),
  uniform4f: vi.fn(),
  uniformMatrix4fv: vi.fn(),
  viewport: vi.fn(),
  clear: vi.fn(),
  clearColor: vi.fn(),
  enable: vi.fn(),
  disable: vi.fn(),
  blendFunc: vi.fn(),
  drawArrays: vi.fn(),
  drawElements: vi.fn(),
  getExtension: vi.fn(() => null),
  getParameter: vi.fn(() => 16384),
  pixelStorei: vi.fn(),
  createFramebuffer: vi.fn(() => ({})),
  bindFramebuffer: vi.fn(),
  framebufferTexture2D: vi.fn(),
  checkFramebufferStatus: vi.fn(() => 36053), // FRAMEBUFFER_COMPLETE
  deleteTexture: vi.fn(),
  deleteBuffer: vi.fn(),
  deleteProgram: vi.fn(),
  deleteShader: vi.fn(),
}

HTMLCanvasElement.prototype.getContext = function (
  contextType: string
): RenderingContext | null {
  if (contextType === 'webgl2' || contextType === 'webgl') {
    return {
      ...mockWebGL2Context,
      canvas: this,
    } as unknown as WebGL2RenderingContext
  }
  return null
}
```

### Test First

Create `src/components/__tests__/NiiVueViewer.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NiiVueViewer } from '../NiiVueViewer'

// Mock the NiiVue module since it requires actual WebGL
vi.mock('@niivue/niivue', () => ({
  Niivue: vi.fn().mockImplementation(() => ({
    attachToCanvas: vi.fn(),
    loadVolumes: vi.fn().mockResolvedValue(undefined),
    setSliceType: vi.fn(),
    opts: {},
  })),
}))

describe('NiiVueViewer', () => {
  const defaultProps = {
    backgroundUrl: 'http://localhost:7860/files/dwi.nii.gz',
  }

  it('renders canvas element', () => {
    render(<NiiVueViewer {...defaultProps} />)

    expect(document.querySelector('canvas')).toBeInTheDocument()
  })

  it('renders container with correct styling', () => {
    render(<NiiVueViewer {...defaultProps} />)

    const container = document.querySelector('canvas')?.parentElement
    expect(container).toHaveClass('bg-gray-900')
  })

  it('renders help text for controls', () => {
    render(<NiiVueViewer {...defaultProps} />)

    expect(screen.getByText(/scroll/i)).toBeInTheDocument()
    expect(screen.getByText(/drag/i)).toBeInTheDocument()
  })

  it('initializes NiiVue with background volume', async () => {
    const { Niivue } = await import('@niivue/niivue')

    render(<NiiVueViewer {...defaultProps} />)

    expect(Niivue).toHaveBeenCalled()
  })

  it('loads overlay when provided', async () => {
    const { Niivue } = await import('@niivue/niivue')
    const mockInstance = {
      attachToCanvas: vi.fn(),
      loadVolumes: vi.fn().mockResolvedValue(undefined),
      opts: {},
    }
    ;(Niivue as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      () => mockInstance
    )

    render(
      <NiiVueViewer
        {...defaultProps}
        overlayUrl="http://localhost:7860/files/prediction.nii.gz"
      />
    )

    // Wait for useEffect to run
    await vi.waitFor(() => {
      expect(mockInstance.loadVolumes).toHaveBeenCalled()
    })

    const loadVolumesCall = mockInstance.loadVolumes.mock.calls[0][0]
    expect(loadVolumesCall).toHaveLength(2)
    expect(loadVolumesCall[1].url).toContain('prediction.nii.gz')
  })

  it('sets canvas dimensions', () => {
    render(<NiiVueViewer {...defaultProps} />)

    const canvas = document.querySelector('canvas')
    expect(canvas).toHaveClass('w-full', 'h-[500px]')
  })
})
```

### Implementation

Create `src/components/NiiVueViewer.tsx`:

```typescript
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

    const nv = new Niivue({
      backColor: [0.05, 0.05, 0.05, 1],
      show3Dcrosshair: true,
      crosshairColor: [1, 0, 0, 0.5],
    })

    nv.attachToCanvas(canvasRef.current)
    nvRef.current = nv

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

    nv.loadVolumes(volumes)

    return () => {
      nvRef.current = null
    }
  }, [backgroundUrl, overlayUrl])

  return (
    <div className="bg-gray-900 rounded-lg p-2">
      <canvas ref={canvasRef} className="w-full h-[500px] rounded" />
      <div className="flex gap-4 mt-2 text-xs text-gray-400">
        <span>Scroll: Navigate slices</span>
        <span>Drag: Adjust contrast</span>
        <span>Right-click: Pan</span>
      </div>
    </div>
  )
}
```

### Verify

```bash
npm test -- NiiVueViewer
# Expected: 6 tests passing
```

---

## Update Component Index

Update `src/components/index.ts`:

```typescript
export { Layout } from './Layout'
export { MetricsPanel } from './MetricsPanel'
export { CaseSelector } from './CaseSelector'
export { NiiVueViewer } from './NiiVueViewer'
```

---

## Visual Verification

Update `src/App.tsx` to preview all components:

```typescript
import { useState } from 'react'
import { Layout } from './components/Layout'
import { CaseSelector } from './components/CaseSelector'
import { MetricsPanel } from './components/MetricsPanel'
import { NiiVueViewer } from './components/NiiVueViewer'

const mockMetrics = {
  caseId: 'sub-stroke0001',
  diceScore: 0.847,
  volumeMl: 15.32,
  elapsedSeconds: 12.5,
}

// Demo NIfTI file from NiiVue examples
const DEMO_NIFTI = 'https://niivue.github.io/niivue-demo-images/mni152.nii.gz'

function App() {
  const [selectedCase, setSelectedCase] = useState<string | null>(null)

  return (
    <Layout>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4">
          <CaseSelector
            selectedCase={selectedCase}
            onSelectCase={setSelectedCase}
          />
          <MetricsPanel metrics={mockMetrics} />
        </div>
        <div className="lg:col-span-2">
          <NiiVueViewer backgroundUrl={DEMO_NIFTI} />
        </div>
      </div>
    </Layout>
  )
}

export default App
```

```bash
npm run dev
# Open http://localhost:5173
# Verify:
# - CaseSelector loads and shows cases
# - NiiVue viewer renders 3D brain
# - MetricsPanel displays correctly
```

---

## Verification Checklist

```bash
npm test
# Expected: ~35+ tests passing
```

- [ ] CaseSelector shows loading state
- [ ] CaseSelector fetches and displays cases
- [ ] CaseSelector calls onSelectCase on selection
- [ ] CaseSelector shows error state on API failure
- [ ] NiiVueViewer renders canvas
- [ ] NiiVueViewer initializes NiiVue instance
- [ ] NiiVueViewer loads overlay when provided
- [ ] Visual: All components render correctly in browser

---

## File Structure After This Phase

```
frontend/src/
├── components/
│   ├── __tests__/
│   │   ├── Layout.test.tsx
│   │   ├── MetricsPanel.test.tsx
│   │   ├── CaseSelector.test.tsx
│   │   └── NiiVueViewer.test.tsx
│   ├── Layout.tsx
│   ├── MetricsPanel.tsx
│   ├── CaseSelector.tsx
│   ├── NiiVueViewer.tsx
│   └── index.ts
├── api/
├── hooks/
├── types/
├── test/
│   └── setup.ts (updated with WebGL mocks)
├── mocks/
└── App.tsx (updated)
```

---

## Next Phase

Once verification passes, proceed to **Spec 37.4: App Integration**
