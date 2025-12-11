import { test, expect } from './fixtures'
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
