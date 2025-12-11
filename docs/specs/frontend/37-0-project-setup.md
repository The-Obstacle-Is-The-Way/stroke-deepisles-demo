# Spec 37.0: Frontend Project Setup

**Status**: READY FOR IMPLEMENTATION
**Phase**: 0 of 5
**Depends On**: Spec 36 (Stack Definition)
**Goal**: Scaffold Vite + React + TypeScript project with testing infrastructure

---

## Deliverables

By the end of this phase, you will have:

1. Working Vite dev server (`npm run dev`)
2. TypeScript compilation passing (`npx tsc --noEmit`)
3. Vitest running with a smoke test (`npm test`)
4. Tailwind CSS working
5. MSW configured for API mocking

---

## Step 1: Create Vite Project

```bash
cd /Users/ray/Desktop/CLARITY-DIGITAL-TWIN/stroke-deepisles-demo
npm create vite@latest frontend -- --template react-ts
cd frontend
```

---

## Step 2: Install Dependencies

```bash
# Core dependencies
npm install @niivue/niivue@0.65.0

# Dev dependencies - Testing
npm install -D vitest@2.1.8 @vitest/coverage-v8@2.1.8 @vitest/ui@2.1.8
npm install -D @testing-library/react@16.1.0 @testing-library/jest-dom@6.6.3 @testing-library/user-event@14.5.2
npm install -D jsdom@25.0.1 msw@2.7.0

# Dev dependencies - Styling
npm install -D tailwindcss@4.1.7 @tailwindcss/vite@4.1.7
```

---

## Step 3: Configure package.json Scripts

Replace scripts section:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage"
  }
}
```

---

## Step 4: Configure Vite + Vitest

Replace `vite.config.ts`:

```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: 'dist',
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', 'e2e'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
        'src/mocks/**',
        'src/main.tsx',
      ],
    },
  },
})
```

---

## Step 5: Configure TypeScript

Replace `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

---

## Step 6: Configure Tailwind CSS

Replace `src/index.css`:

```css
@import "tailwindcss";
```

---

## Step 7: Create Test Setup

Create `src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, afterAll } from 'vitest'
import { server } from '../mocks/server'

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Clean up after each test
afterEach(() => {
  cleanup()
  server.resetHandlers()
})

// Clean up after all tests
afterAll(() => server.close())

// Mock ResizeObserver (needed for some UI components)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
```

---

## Step 8: Create MSW Mocks

Create `src/mocks/handlers.ts`:

```typescript
import { http, HttpResponse } from 'msw'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:7860'

export const handlers = [
  // GET /api/cases - List available cases
  http.get(`${API_BASE}/api/cases`, () => {
    return HttpResponse.json({
      cases: ['sub-stroke0001', 'sub-stroke0002', 'sub-stroke0003'],
    })
  }),

  // POST /api/segment - Run segmentation
  http.post(`${API_BASE}/api/segment`, async ({ request }) => {
    const body = (await request.json()) as { case_id: string }
    return HttpResponse.json({
      caseId: body.case_id,
      diceScore: 0.847,
      volumeMl: 15.32,
      elapsedSeconds: 12.5,
      dwiUrl: `${API_BASE}/files/dwi.nii.gz`,
      predictionUrl: `${API_BASE}/files/prediction.nii.gz`,
    })
  }),
]
```

Create `src/mocks/server.ts`:

```typescript
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

---

## Step 9: Create Smoke Test

Create `src/App.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    // This will pass with default Vite template
    expect(document.body).toBeInTheDocument()
  })
})
```

---

## Step 10: Create Environment File

Create `.env`:

```env
VITE_API_URL=http://localhost:7860
```

Create `.env.example`:

```env
VITE_API_URL=http://localhost:7860
```

---

## Verification Checklist

Run these commands to verify setup:

```bash
# 1. TypeScript compiles
npx tsc --noEmit
# Expected: No errors

# 2. Dev server starts
npm run dev
# Expected: Server at http://localhost:5173

# 3. Tests pass
npm test
# Expected: 1 test passing

# 4. Build works
npm run build
# Expected: dist/ folder created
```

---

## File Structure After This Phase

```
frontend/
├── src/
│   ├── mocks/
│   │   ├── handlers.ts
│   │   └── server.ts
│   ├── test/
│   │   └── setup.ts
│   ├── App.tsx
│   ├── App.test.tsx
│   ├── main.tsx
│   └── index.css
├── .env
├── .env.example
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## Next Phase

Once verification passes, proceed to **Spec 37.1: Foundation Components**
