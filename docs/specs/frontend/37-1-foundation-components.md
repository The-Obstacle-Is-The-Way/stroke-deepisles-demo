# Spec 37.1: Foundation Components

**Status**: READY FOR IMPLEMENTATION
**Phase**: 1 of 5
**Depends On**: Spec 37.0 (Project Setup)
**Goal**: TDD implementation of Layout and MetricsPanel components

---

## Deliverables

By the end of this phase, you will have:

1. `Layout` component with header and main content area
2. `MetricsPanel` component displaying segmentation results
3. 100% test coverage for both components
4. Visual verification in browser

---

## Component 1: Layout

### Test First

Create `src/components/__tests__/Layout.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Layout } from '../Layout'

describe('Layout', () => {
  it('renders header with title', () => {
    render(<Layout>Content</Layout>)

    expect(
      screen.getByRole('heading', { name: /stroke lesion segmentation/i })
    ).toBeInTheDocument()
  })

  it('renders subtitle', () => {
    render(<Layout>Content</Layout>)

    expect(screen.getByText(/deepisles segmentation/i)).toBeInTheDocument()
  })

  it('renders children in main area', () => {
    render(
      <Layout>
        <div data-testid="child">Test Child</div>
      </Layout>
    )

    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('has accessible landmark structure', () => {
    render(<Layout>Content</Layout>)

    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('applies dark theme styling', () => {
    render(<Layout>Content</Layout>)

    const container = screen.getByRole('banner').parentElement
    expect(container).toHaveClass('bg-gray-950')
  })
})
```

### Implementation

Create `src/components/Layout.tsx`:

```typescript
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
      <main className="container mx-auto px-4 py-6">{children}</main>
    </div>
  )
}
```

### Verify

```bash
npm test -- Layout
# Expected: 5 tests passing
```

---

## Component 2: MetricsPanel

### Test First

Create `src/components/__tests__/MetricsPanel.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MetricsPanel } from '../MetricsPanel'

describe('MetricsPanel', () => {
  const defaultMetrics = {
    caseId: 'sub-stroke0001',
    diceScore: 0.847,
    volumeMl: 15.32,
    elapsedSeconds: 12.5,
  }

  it('renders results heading', () => {
    render(<MetricsPanel metrics={defaultMetrics} />)

    expect(
      screen.getByRole('heading', { name: /results/i })
    ).toBeInTheDocument()
  })

  it('displays case ID', () => {
    render(<MetricsPanel metrics={defaultMetrics} />)

    expect(screen.getByText('sub-stroke0001')).toBeInTheDocument()
  })

  it('displays dice score with 3 decimal places', () => {
    render(<MetricsPanel metrics={defaultMetrics} />)

    expect(screen.getByText('0.847')).toBeInTheDocument()
  })

  it('displays volume in mL with 2 decimal places', () => {
    render(<MetricsPanel metrics={defaultMetrics} />)

    expect(screen.getByText('15.32 mL')).toBeInTheDocument()
  })

  it('displays elapsed time with 1 decimal place', () => {
    render(<MetricsPanel metrics={defaultMetrics} />)

    expect(screen.getByText('12.5s')).toBeInTheDocument()
  })

  it('hides dice score row when null', () => {
    render(
      <MetricsPanel metrics={{ ...defaultMetrics, diceScore: null }} />
    )

    expect(screen.queryByText(/dice score/i)).not.toBeInTheDocument()
  })

  it('hides volume row when null', () => {
    render(
      <MetricsPanel metrics={{ ...defaultMetrics, volumeMl: null }} />
    )

    expect(screen.queryByText(/volume/i)).not.toBeInTheDocument()
  })

  it('applies card styling', () => {
    render(<MetricsPanel metrics={defaultMetrics} />)

    const panel = screen.getByRole('heading', { name: /results/i }).parentElement
    expect(panel).toHaveClass('bg-gray-800', 'rounded-lg')
  })
})
```

### Implementation

Create `src/components/MetricsPanel.tsx`:

```typescript
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
            <span className="ml-2 font-mono">
              {metrics.volumeMl.toFixed(2)} mL
            </span>
          </div>
        )}

        <div>
          <span className="text-gray-400">Time:</span>
          <span className="ml-2 font-mono">
            {metrics.elapsedSeconds.toFixed(1)}s
          </span>
        </div>
      </div>
    </div>
  )
}
```

### Verify

```bash
npm test -- MetricsPanel
# Expected: 8 tests passing
```

---

## Create Index Export

Create `src/components/index.ts`:

```typescript
export { Layout } from './Layout'
export { MetricsPanel } from './MetricsPanel'
```

---

## Visual Verification

Update `src/App.tsx` to see components:

```typescript
import { Layout } from './components/Layout'
import { MetricsPanel } from './components/MetricsPanel'

const mockMetrics = {
  caseId: 'sub-stroke0001',
  diceScore: 0.847,
  volumeMl: 15.32,
  elapsedSeconds: 12.5,
}

function App() {
  return (
    <Layout>
      <div className="max-w-md">
        <MetricsPanel metrics={mockMetrics} />
      </div>
    </Layout>
  )
}

export default App
```

Run dev server and verify visually:

```bash
npm run dev
# Open http://localhost:5173
```

---

## Verification Checklist

- [ ] `npm test` - All 13+ tests pass
- [ ] `npm run dev` - Components render correctly
- [ ] Header shows "Stroke Lesion Segmentation"
- [ ] MetricsPanel shows all metrics with correct formatting
- [ ] Dark theme applies correctly

---

## File Structure After This Phase

```
frontend/src/
├── components/
│   ├── __tests__/
│   │   ├── Layout.test.tsx
│   │   └── MetricsPanel.test.tsx
│   ├── Layout.tsx
│   ├── MetricsPanel.tsx
│   └── index.ts
├── mocks/
├── test/
├── App.tsx (updated)
└── ...
```

---

## Next Phase

Once verification passes, proceed to **Spec 37.2: API Layer**
