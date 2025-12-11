# Spec 37.5: E2E Tests & CI/CD

**Status**: READY FOR IMPLEMENTATION
**Phase**: 5 of 5
**Depends On**: Spec 37.4 (App Integration)
**Goal**: End-to-end tests with Playwright and GitHub Actions CI pipeline

---

## Deliverables

By the end of this phase, you will have:

1. Playwright E2E tests for critical user flows
2. Page Object Models for maintainable tests
3. GitHub Actions workflow for CI
4. Coverage reporting integration

---

## Step 1: Install Playwright

```bash
cd frontend
npm install -D @playwright/test@1.49.1
npx playwright install
```

---

## Step 2: Playwright Configuration

Create `playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
    ...(process.env.CI ? [['github' as const]] : []),
  ],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment for cross-browser testing:
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
```

---

## Step 3: Update package.json Scripts

Add to `package.json` scripts:

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:debug": "playwright test --debug"
  }
}
```

---

## Step 4: Page Object Model

Create `e2e/pages/HomePage.ts`:

```typescript
import { type Page, type Locator, expect } from '@playwright/test'

export class HomePage {
  readonly page: Page
  readonly heading: Locator
  readonly caseSelector: Locator
  readonly runButton: Locator
  readonly processingText: Locator
  readonly metricsPanel: Locator
  readonly diceScore: Locator
  readonly viewer: Locator
  readonly placeholderText: Locator
  readonly errorAlert: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', {
      name: /stroke lesion segmentation/i,
    })
    this.caseSelector = page.getByRole('combobox')
    this.runButton = page.getByRole('button', { name: /run segmentation/i })
    this.processingText = page.getByText(/processing/i)
    this.metricsPanel = page.getByRole('heading', { name: /results/i })
    this.diceScore = page.getByText(/0\.\d{3}/)
    this.viewer = page.locator('canvas')
    this.placeholderText = page.getByText(/select a case and run segmentation/i)
    this.errorAlert = page.getByRole('alert')
  }

  async goto() {
    await this.page.goto('/')
    await expect(this.heading).toBeVisible()
  }

  async waitForCasesToLoad() {
    await expect(this.caseSelector).toBeEnabled({ timeout: 10000 })
  }

  async selectCase(caseId: string) {
    await this.caseSelector.selectOption(caseId)
  }

  async runSegmentation() {
    await this.runButton.click()
  }

  async waitForResults() {
    await expect(this.metricsPanel).toBeVisible({ timeout: 30000 })
  }

  async expectViewerVisible() {
    await expect(this.viewer).toBeVisible()
  }

  async expectPlaceholderVisible() {
    await expect(this.placeholderText).toBeVisible()
  }

  async expectErrorVisible() {
    await expect(this.errorAlert).toBeVisible()
  }
}
```

---

## Step 5: E2E Tests

Create `e2e/home.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'
import { HomePage } from './pages/HomePage'

test.describe('Home Page', () => {
  test('displays main heading', async ({ page }) => {
    const homePage = new HomePage(page)
    await homePage.goto()

    await expect(homePage.heading).toBeVisible()
  })

  test('loads case selector with options', async ({ page }) => {
    const homePage = new HomePage(page)
    await homePage.goto()
    await homePage.waitForCasesToLoad()

    // Verify selector has options
    const options = await homePage.caseSelector.locator('option').count()
    expect(options).toBeGreaterThan(1) // placeholder + cases
  })

  test('shows placeholder viewer initially', async ({ page }) => {
    const homePage = new HomePage(page)
    await homePage.goto()

    await homePage.expectPlaceholderVisible()
  })

  test('run button disabled without case selected', async ({ page }) => {
    const homePage = new HomePage(page)
    await homePage.goto()
    await homePage.waitForCasesToLoad()

    await expect(homePage.runButton).toBeDisabled()
  })
})
```

Create `e2e/segmentation-flow.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'
import { HomePage } from './pages/HomePage'

test.describe('Segmentation Flow', () => {
  test('complete segmentation workflow', async ({ page }) => {
    const homePage = new HomePage(page)
    await homePage.goto()
    await homePage.waitForCasesToLoad()

    // Select a case
    await homePage.selectCase('sub-stroke0001')
    await expect(homePage.runButton).toBeEnabled()

    // Run segmentation
    await homePage.runSegmentation()

    // Verify processing state
    await expect(homePage.processingText).toBeVisible()

    // Wait for results
    await homePage.waitForResults()

    // Verify results displayed
    await expect(homePage.diceScore).toBeVisible()
    await homePage.expectViewerVisible()

    // Placeholder should be gone
    await expect(homePage.placeholderText).not.toBeVisible()
  })

  test('can run multiple segmentations', async ({ page }) => {
    const homePage = new HomePage(page)
    await homePage.goto()
    await homePage.waitForCasesToLoad()

    // First run
    await homePage.selectCase('sub-stroke0001')
    await homePage.runSegmentation()
    await homePage.waitForResults()

    // Second run with different case
    await homePage.selectCase('sub-stroke0002')
    await homePage.runSegmentation()
    await homePage.waitForResults()

    // Results should still be visible
    await expect(homePage.metricsPanel).toBeVisible()
  })
})
```

Create `e2e/error-handling.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'
import { HomePage } from './pages/HomePage'

test.describe('Error Handling', () => {
  test('shows error when API fails', async ({ page }) => {
    // Mock API to return error
    await page.route('**/api/segment', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Segmentation failed' }),
      })
    })

    const homePage = new HomePage(page)
    await homePage.goto()
    await homePage.waitForCasesToLoad()

    await homePage.selectCase('sub-stroke0001')
    await homePage.runSegmentation()

    await homePage.expectErrorVisible()
    await expect(homePage.errorAlert).toContainText(/failed/i)
  })

  test('shows error when cases fail to load', async ({ page }) => {
    // Mock cases API to return error
    await page.route('**/api/cases', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Server error' }),
      })
    })

    const homePage = new HomePage(page)
    await homePage.goto()

    // Case selector should show error state
    await expect(page.getByText(/failed to load/i)).toBeVisible()
  })
})
```

---

## Step 6: GitHub Actions CI Workflow

Create `.github/workflows/frontend-ci.yml`:

```yaml
name: Frontend CI

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-ci.yml'
  pull_request:
    paths:
      - 'frontend/**'

defaults:
  run:
    working-directory: frontend

jobs:
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - run: npm ci
      - run: npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - run: npm ci
      - run: npm run test:coverage

      - uses: codecov/codecov-action@v4
        with:
          files: frontend/coverage/coverage-final.json
          flags: frontend
          fail_ci_if_error: false

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - run: npm ci
      - run: npx playwright install --with-deps chromium

      - run: npm run test:e2e

      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 7

  build:
    runs-on: ubuntu-latest
    needs: [typecheck, test]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - run: npm ci
      - run: npm run build

      - uses: actions/upload-artifact@v4
        with:
          name: frontend-dist
          path: frontend/dist/
          retention-days: 7
```

---

## Step 7: Add Coverage Thresholds

Update `vite.config.ts` coverage section:

```typescript
coverage: {
  provider: 'v8',
  reporter: ['text', 'json', 'html'],
  include: ['src/**/*.{ts,tsx}'],
  exclude: [
    'src/**/*.test.{ts,tsx}',
    'src/test/**',
    'src/mocks/**',
    'src/main.tsx',
    'src/vite-env.d.ts',
  ],
  thresholds: {
    statements: 80,
    branches: 75,
    functions: 80,
    lines: 80,
  },
},
```

---

## Step 8: Run All Tests

```bash
# Unit & Integration tests
npm test
# Expected: ~45+ tests passing

# E2E tests
npm run test:e2e
# Expected: 7 tests passing

# Coverage report
npm run test:coverage
# Expected: >80% coverage
```

---

## Verification Checklist

- [ ] `npm test` - All unit/integration tests pass
- [ ] `npm run test:coverage` - Coverage meets thresholds
- [ ] `npm run test:e2e` - All E2E tests pass
- [ ] `npm run build` - Production build succeeds
- [ ] CI workflow runs successfully (push to branch)

---

## File Structure After This Phase

```
frontend/
├── e2e/
│   ├── pages/
│   │   └── HomePage.ts
│   ├── home.spec.ts
│   ├── segmentation-flow.spec.ts
│   └── error-handling.spec.ts
├── src/
│   ├── components/
│   ├── api/
│   ├── hooks/
│   ├── types/
│   ├── test/
│   ├── mocks/
│   ├── App.tsx
│   ├── App.test.tsx
│   └── ...
├── .github/
│   └── workflows/
│       └── frontend-ci.yml
├── playwright.config.ts
├── vite.config.ts
├── package.json
└── ...
```

---

## Summary: Complete Testing Stack

| Layer | Tool | Test Count | Purpose |
|-------|------|------------|---------|
| Unit | Vitest + RTL | ~35 | Component isolation |
| Integration | Vitest + MSW | ~15 | API + hooks |
| E2E | Playwright | ~7 | Full user flows |
| **Total** | | **~57** | |

---

## Next Steps After All Phases Complete

1. **Deploy Frontend**: Push to HuggingFace Static Space
2. **Connect to Backend**: Update `VITE_API_URL` to real backend
3. **Test Against Real API**: Run E2E tests with real backend
4. **Monitor**: Set up error tracking (optional)

---

## Congratulations!

You now have a fully tested React frontend with:

- Type-safe TypeScript code
- Comprehensive unit tests
- API mocking with MSW
- End-to-end browser tests
- Automated CI/CD pipeline
- 80%+ code coverage
