import { test, expect } from './fixtures'
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
