import { test as base, expect } from '@playwright/test'

// API response mocks matching MSW handlers
const MOCK_CASES = ['sub-stroke0001', 'sub-stroke0002', 'sub-stroke0003']
const MOCK_SEGMENT_RESPONSE = {
  caseId: 'sub-stroke0001',
  diceScore: 0.847,
  volumeMl: 15.32,
  elapsedSeconds: 12.5,
  // Use real public NIfTI for visual testing (NiiVue demo image)
  dwiUrl: 'https://niivue.github.io/niivue-demo-images/mni152.nii.gz',
  predictionUrl: 'https://niivue.github.io/niivue-demo-images/mni152.nii.gz',
}

// Extend base test to include API mocking
export const test = base.extend({
  // Auto-mock API routes for every test
  page: async ({ page }, use) => {
    // Mock GET /api/cases
    await page.route('**/api/cases', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ cases: MOCK_CASES }),
      })
    })

    // Mock POST /api/segment - return different caseId based on request
    await page.route('**/api/segment', async (route) => {
      const request = route.request()
      const body = JSON.parse(request.postData() || '{}') as { case_id?: string }

      // Simulate network delay
      await new Promise((r) => setTimeout(r, 200))

      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...MOCK_SEGMENT_RESPONSE,
          caseId: body.case_id || 'sub-stroke0001',
        }),
      })
    })

    await use(page)
  },
})

export { expect }
