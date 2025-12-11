import { test as base, expect } from '@playwright/test'
import { HomePage } from './pages/HomePage'

// Error tests need to override the default mocks, so use base test
const test = base

test.describe('Error Handling', () => {
  test('shows error when API fails', async ({ page }) => {
    // Mock cases API (needed for page to load)
    await page.route('**/api/cases', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ cases: ['sub-stroke0001'] }),
      })
    })

    // Mock segment API to return error
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
