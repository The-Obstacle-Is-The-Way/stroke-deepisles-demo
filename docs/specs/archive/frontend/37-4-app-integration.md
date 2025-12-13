# Spec 37.4: App Integration

**Status**: READY FOR IMPLEMENTATION
**Phase**: 4 of 5
**Depends On**: Spec 37.3 (Interactive Components)
**Goal**: Wire all components together into a working application

---

## Deliverables

By the end of this phase, you will have:

1. Complete `App.tsx` with full user flow
2. Integration tests for the complete workflow
3. Error handling for all states
4. Working end-to-end flow (with mocked API)

---

## Step 1: App Integration Tests

Create `src/App.test.tsx`:

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { server } from './mocks/server'
import { errorHandlers } from './mocks/handlers'
import App from './App'

describe('App Integration', () => {
  describe('Initial Render', () => {
    it('renders main heading', () => {
      render(<App />)

      expect(
        screen.getByRole('heading', { name: /stroke lesion segmentation/i })
      ).toBeInTheDocument()
    })

    it('renders case selector', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })
    })

    it('renders run button', () => {
      render(<App />)

      expect(
        screen.getByRole('button', { name: /run segmentation/i })
      ).toBeInTheDocument()
    })

    it('shows placeholder viewer message', () => {
      render(<App />)

      expect(
        screen.getByText(/select a case and run segmentation/i)
      ).toBeInTheDocument()
    })
  })

  describe('Run Button State', () => {
    it('disables run button when no case selected', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      expect(
        screen.getByRole('button', { name: /run segmentation/i })
      ).toBeDisabled()
    })

    it('enables run button when case selected', async () => {
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')

      expect(
        screen.getByRole('button', { name: /run segmentation/i })
      ).toBeEnabled()
    })
  })

  describe('Segmentation Flow', () => {
    it('shows processing state when running', async () => {
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      expect(screen.getByText(/processing/i)).toBeInTheDocument()
    })

    it('displays metrics after successful segmentation', async () => {
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByText('0.847')).toBeInTheDocument()
      })

      expect(screen.getByText('15.32 mL')).toBeInTheDocument()
      expect(screen.getByText(/12\.5s/)).toBeInTheDocument()
    })

    it('displays viewer after successful segmentation', async () => {
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(document.querySelector('canvas')).toBeInTheDocument()
      })
    })

    it('hides placeholder after successful segmentation', async () => {
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByText('0.847')).toBeInTheDocument()
      })

      expect(
        screen.queryByText(/select a case and run segmentation/i)
      ).not.toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('shows error when segmentation fails', async () => {
      server.use(errorHandlers.segmentServerError)
      const user = userEvent.setup()

      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      expect(screen.getByText(/segmentation failed/i)).toBeInTheDocument()
    })

    it('allows retry after error', async () => {
      server.use(errorHandlers.segmentServerError)
      const user = userEvent.setup()

      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })

      // Reset to success handler
      server.resetHandlers()

      // Retry
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByText('0.847')).toBeInTheDocument()
      })

      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  describe('Multiple Runs', () => {
    it('allows running segmentation on different cases', async () => {
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument()
      })

      // First case
      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0001')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByText('sub-stroke0001')).toBeInTheDocument()
      })

      // Second case
      await user.selectOptions(screen.getByRole('combobox'), 'sub-stroke0002')
      await user.click(screen.getByRole('button', { name: /run segmentation/i }))

      await waitFor(() => {
        expect(screen.getByText('sub-stroke0002')).toBeInTheDocument()
      })
    })
  })
})
```

---

## Step 2: App Implementation

Replace `src/App.tsx`:

```typescript
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
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600
                       disabled:cursor-not-allowed text-white font-medium
                       py-3 px-4 rounded-lg transition-colors"
          >
            {isLoading ? 'Processing...' : 'Run Segmentation'}
          </button>

          {error && (
            <div role="alert" className="bg-red-900/50 text-red-300 p-3 rounded-lg">
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

---

## Step 3: Run Tests

```bash
npm test
# Expected: ~45+ tests passing
```

---

## Step 4: Visual Verification

```bash
npm run dev
# Open http://localhost:5173
```

**Manual Test Checklist:**

1. [ ] Page loads with header
2. [ ] Case selector shows "Loading cases..."
3. [ ] Case selector populates with 3 cases
4. [ ] Run button is disabled initially
5. [ ] Selecting a case enables run button
6. [ ] Clicking run shows "Processing..."
7. [ ] After completion, metrics panel appears
8. [ ] After completion, viewer shows (with demo image)
9. [ ] Selecting different case and running updates results

---

## Step 5: Test Custom Render Utility (Optional Enhancement)

Create `src/test/test-utils.tsx`:

```typescript
import type { ReactElement, ReactNode } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Wrapper for any providers (Router, Theme, etc.)
function AllTheProviders({ children }: { children: ReactNode }) {
  return <>{children}</>
}

function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper: AllTheProviders, ...options }),
  }
}

// Re-export everything
export * from '@testing-library/react'
export { customRender as render }
```

Update tests to use custom render (optional):

```typescript
import { render, screen, waitFor } from '../test/test-utils'
// Now `render` returns `{ user, ...result }`
```

---

## Verification Checklist

```bash
# All tests pass
npm test
# Expected: ~45+ tests passing

# Build succeeds
npm run build
# Expected: dist/ folder created

# No TypeScript errors
npx tsc --noEmit
# Expected: No errors
```

- [ ] All integration tests pass
- [ ] Full flow works in browser
- [ ] Error states display correctly
- [ ] Loading states display correctly
- [ ] Results update on new runs

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
│   ├── __tests__/
│   │   └── client.test.ts
│   ├── client.ts
│   └── index.ts
├── hooks/
│   ├── __tests__/
│   │   └── useSegmentation.test.tsx
│   ├── useSegmentation.ts
│   └── index.ts
├── types/
│   └── index.ts
├── test/
│   ├── setup.ts
│   ├── fixtures.ts
│   └── test-utils.tsx
├── mocks/
│   ├── handlers.ts
│   └── server.ts
├── App.tsx
├── App.test.tsx
├── main.tsx
└── index.css
```

---

## Next Phase

Once verification passes, proceed to **Spec 37.5: E2E Tests & CI/CD**
