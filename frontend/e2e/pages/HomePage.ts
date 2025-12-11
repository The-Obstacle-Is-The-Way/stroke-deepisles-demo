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
