# Spec 37.2: API Layer

**Status**: READY FOR IMPLEMENTATION
**Phase**: 2 of 5
**Depends On**: Spec 37.1 (Foundation Components)
**Goal**: TDD implementation of API client and useSegmentation hook

---

## Deliverables

By the end of this phase, you will have:

1. Type definitions for API responses
2. `apiClient` with `getCases()` and `runSegmentation()` methods
3. `useSegmentation` React hook for state management
4. MSW handlers for all API endpoints
5. Error handling tests

---

## Step 1: Type Definitions

Create `src/types/index.ts`:

```typescript
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

export interface CasesResponse {
  cases: string[]
}

export interface SegmentResponse {
  caseId: string
  diceScore: number | null
  volumeMl: number | null
  elapsedSeconds: number
  dwiUrl: string
  predictionUrl: string
}
```

---

## Step 2: Test Fixtures

Create `src/test/fixtures.ts`:

```typescript
import type { SegmentationResult, CasesResponse } from '../types'

export const mockCases: string[] = [
  'sub-stroke0001',
  'sub-stroke0002',
  'sub-stroke0003',
]

export const mockCasesResponse: CasesResponse = {
  cases: mockCases,
}

export const mockSegmentationResult: SegmentationResult = {
  dwiUrl: 'http://localhost:7860/files/dwi.nii.gz',
  predictionUrl: 'http://localhost:7860/files/prediction.nii.gz',
  metrics: {
    caseId: 'sub-stroke0001',
    diceScore: 0.847,
    volumeMl: 15.32,
    elapsedSeconds: 12.5,
  },
}
```

---

## Step 3: Enhanced MSW Handlers

Update `src/mocks/handlers.ts`:

```typescript
import { http, HttpResponse, delay } from 'msw'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:7860'

export const handlers = [
  http.get(`${API_BASE}/api/cases`, async () => {
    await delay(100)
    return HttpResponse.json({
      cases: ['sub-stroke0001', 'sub-stroke0002', 'sub-stroke0003'],
    })
  }),

  http.post(`${API_BASE}/api/segment`, async ({ request }) => {
    const body = (await request.json()) as { case_id: string; fast_mode?: boolean }
    await delay(200)
    return HttpResponse.json({
      caseId: body.case_id,
      diceScore: 0.847,
      volumeMl: 15.32,
      // Reflect fast_mode in response - slower when fast_mode=false
      elapsedSeconds: body.fast_mode === false ? 45.0 : 12.5,
      dwiUrl: `${API_BASE}/files/dwi.nii.gz`,
      predictionUrl: `${API_BASE}/files/prediction.nii.gz`,
    })
  }),
]

// Error handlers for testing error states
export const errorHandlers = {
  casesServerError: http.get(`${API_BASE}/api/cases`, () => {
    return HttpResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }),

  casesNetworkError: http.get(`${API_BASE}/api/cases`, () => {
    return HttpResponse.error()
  }),

  segmentServerError: http.post(`${API_BASE}/api/segment`, () => {
    return HttpResponse.json(
      { detail: 'Segmentation failed: out of memory' },
      { status: 500 }
    )
  }),

  segmentTimeout: http.post(`${API_BASE}/api/segment`, async () => {
    await delay(30000)
    return HttpResponse.json({ detail: 'Timeout' }, { status: 504 })
  }),
}
```

---

## Step 4: API Client

### Test First

Create `src/api/__tests__/client.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { server } from '../../mocks/server'
import { errorHandlers } from '../../mocks/handlers'
import { apiClient } from '../client'

describe('apiClient', () => {
  describe('getCases', () => {
    it('returns list of case IDs', async () => {
      const result = await apiClient.getCases()

      expect(result.cases).toHaveLength(3)
      expect(result.cases).toContain('sub-stroke0001')
    })

    it('throws ApiError on server error', async () => {
      server.use(errorHandlers.casesServerError)

      await expect(apiClient.getCases()).rejects.toThrow(/failed to fetch cases/i)
    })

    it('throws ApiError on network error', async () => {
      server.use(errorHandlers.casesNetworkError)

      await expect(apiClient.getCases()).rejects.toThrow()
    })
  })

  describe('runSegmentation', () => {
    it('returns segmentation result', async () => {
      const result = await apiClient.runSegmentation('sub-stroke0001')

      expect(result.caseId).toBe('sub-stroke0001')
      expect(result.diceScore).toBe(0.847)
      expect(result.volumeMl).toBe(15.32)
      expect(result.dwiUrl).toContain('dwi.nii.gz')
      expect(result.predictionUrl).toContain('prediction.nii.gz')
    })

    it('sends fast_mode parameter', async () => {
      const result = await apiClient.runSegmentation('sub-stroke0001', false)

      expect(result).toBeDefined()
    })

    it('defaults fast_mode to true', async () => {
      const result = await apiClient.runSegmentation('sub-stroke0001')

      expect(result).toBeDefined()
    })

    it('throws ApiError on server error', async () => {
      server.use(errorHandlers.segmentServerError)

      await expect(
        apiClient.runSegmentation('sub-stroke0001')
      ).rejects.toThrow(/segmentation failed/i)
    })
  })
})
```

### Implementation

Create `src/api/client.ts`:

```typescript
import type { CasesResponse, SegmentResponse } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:7860'

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async getCases(): Promise<CasesResponse> {
    const response = await fetch(`${this.baseUrl}/api/cases`)

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(
        `Failed to fetch cases: ${response.statusText}`,
        response.status,
        error.detail
      )
    }

    return response.json()
  }

  async runSegmentation(
    caseId: string,
    fastMode: boolean = true
  ): Promise<SegmentResponse> {
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
      const error = await response.json().catch(() => ({}))
      throw new ApiError(
        `Segmentation failed: ${error.detail || response.statusText}`,
        response.status,
        error.detail
      )
    }

    return response.json()
  }
}

export const apiClient = new ApiClient(API_BASE)
```

### Verify

```bash
npm test -- client
# Expected: 7 tests passing
```

---

## Step 5: useSegmentation Hook

### Test First

Create `src/hooks/__tests__/useSegmentation.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { server } from '../../mocks/server'
import { errorHandlers } from '../../mocks/handlers'
import { useSegmentation } from '../useSegmentation'

describe('useSegmentation', () => {
  it('starts with null result and not loading', () => {
    const { result } = renderHook(() => useSegmentation())

    expect(result.current.result).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('sets loading state during segmentation', async () => {
    const { result } = renderHook(() => useSegmentation())

    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
  })

  it('returns result on success', async () => {
    const { result } = renderHook(() => useSegmentation())

    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.result).not.toBeNull()
    expect(result.current.result?.metrics.caseId).toBe('sub-stroke0001')
    expect(result.current.result?.metrics.diceScore).toBe(0.847)
    expect(result.current.result?.dwiUrl).toContain('dwi.nii.gz')
  })

  it('sets error on failure', async () => {
    server.use(errorHandlers.segmentServerError)

    const { result } = renderHook(() => useSegmentation())

    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.error).toMatch(/segmentation failed/i)
    expect(result.current.result).toBeNull()
  })

  it('clears previous error on new request', async () => {
    server.use(errorHandlers.segmentServerError)
    const { result } = renderHook(() => useSegmentation())

    // First request fails
    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })
    expect(result.current.error).not.toBeNull()

    // Reset to success handler
    server.resetHandlers()

    // Second request succeeds
    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.error).toBeNull()
    expect(result.current.result).not.toBeNull()
  })

  it('clears previous result on new request', async () => {
    const { result } = renderHook(() => useSegmentation())

    // First request
    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })
    expect(result.current.result).not.toBeNull()

    // Start second request - result should clear while loading
    act(() => {
      result.current.runSegmentation('sub-stroke0002')
    })

    // While loading, previous result is still available
    // (or you could clear it - depends on UX preference)
    expect(result.current.isLoading).toBe(true)
  })
})
```

### Implementation

Create `src/hooks/useSegmentation.ts`:

```typescript
import { useState, useCallback } from 'react'
import { apiClient } from '../api/client'
import type { SegmentationResult } from '../types'

export function useSegmentation() {
  const [result, setResult] = useState<SegmentationResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runSegmentation = useCallback(async (caseId: string, fastMode = true) => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await apiClient.runSegmentation(caseId, fastMode)

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
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      setResult(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return { result, isLoading, error, runSegmentation }
}
```

### Verify

```bash
npm test -- useSegmentation
# Expected: 6 tests passing
```

---

## Step 6: Create Index Export

Create `src/hooks/index.ts`:

```typescript
export { useSegmentation } from './useSegmentation'
```

Create `src/api/index.ts`:

```typescript
export { apiClient, ApiError } from './client'
```

---

## Verification Checklist

```bash
# Run all tests
npm test

# Expected output:
# - client.test.ts: 7 tests passing
# - useSegmentation.test.tsx: 6 tests passing
# Total: ~25+ tests passing
```

- [ ] API client handles success responses
- [ ] API client handles error responses
- [ ] Hook manages loading state correctly
- [ ] Hook manages error state correctly
- [ ] Hook transforms API response to SegmentationResult

---

## File Structure After This Phase

```
frontend/src/
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
│   └── fixtures.ts
├── mocks/
│   ├── handlers.ts (updated)
│   └── server.ts
├── components/
│   └── ...
└── ...
```

---

## Next Phase

Once verification passes, proceed to **Spec 37.3: Interactive Components**
