import { test as base, expect, Page } from '@playwright/test'

// API response mocks matching the async job queue pattern
const MOCK_CASES = ['sub-stroke0001', 'sub-stroke0002', 'sub-stroke0003']

// Track jobs for the async pattern
interface MockJob {
  id: string
  caseId: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  progressMessage: string
  createdAt: number
}

// Job store per test (reset for each test)
const createJobStore = () => {
  const jobs = new Map<string, MockJob>()
  let jobCounter = 0

  return {
    createJob(caseId: string): MockJob {
      const jobId = `e2e-job-${++jobCounter}`
      const job: MockJob = {
        id: jobId,
        caseId,
        status: 'pending',
        progress: 0,
        progressMessage: 'Job queued',
        createdAt: Date.now(),
      }
      jobs.set(jobId, job)
      return job
    },
    getJob(jobId: string): MockJob | undefined {
      return jobs.get(jobId)
    },
    updateJobProgress(job: MockJob): MockJob {
      // Simulate job progression over 1 second
      const elapsed = Date.now() - job.createdAt
      if (elapsed < 200) {
        return { ...job, status: 'running', progress: 25, progressMessage: 'Loading case data...' }
      } else if (elapsed < 500) {
        return { ...job, status: 'running', progress: 50, progressMessage: 'Running inference...' }
      } else if (elapsed < 800) {
        return { ...job, status: 'running', progress: 75, progressMessage: 'Processing results...' }
      } else {
        return { ...job, status: 'completed', progress: 100, progressMessage: 'Segmentation complete' }
      }
    },
  }
}

// Mock completed job result
const createMockResult = (caseId: string) => ({
  caseId,
  diceScore: 0.847,
  volumeMl: 15.32,
  elapsedSeconds: 12.5,
  // Use real public NIfTI for visual testing (NiiVue demo image)
  dwiUrl: 'https://niivue.github.io/niivue-demo-images/mni152.nii.gz',
  predictionUrl: 'https://niivue.github.io/niivue-demo-images/mni152.nii.gz',
})

// Setup API mocking for async job queue pattern
async function setupApiMocks(page: Page) {
  const jobStore = createJobStore()

  // Mock GET /api/cases
  await page.route('**/api/cases', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ cases: MOCK_CASES }),
    })
  })

  // Mock POST /api/segment - returns 202 with job ID (async pattern)
  await page.route('**/api/segment', async (route) => {
    const request = route.request()
    const body = JSON.parse(request.postData() || '{}') as { case_id?: string }
    const caseId = body.case_id || 'sub-stroke0001'

    // Create a new job
    const job = jobStore.createJob(caseId)

    // Small delay to simulate network
    await new Promise((r) => setTimeout(r, 50))

    route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({
        jobId: job.id,
        status: 'pending',
        message: `Segmentation job queued for ${caseId}`,
      }),
    })
  })

  // Mock GET /api/jobs/:jobId - returns job status (for polling)
  await page.route('**/api/jobs/*', async (route) => {
    const url = route.request().url()
    const jobId = url.split('/api/jobs/')[1]

    const job = jobStore.getJob(jobId)
    if (!job) {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: `Job not found: ${jobId}` }),
      })
      return
    }

    // Update job progress based on elapsed time
    const updatedJob = jobStore.updateJobProgress(job)

    const response: Record<string, unknown> = {
      jobId: updatedJob.id,
      status: updatedJob.status,
      progress: updatedJob.progress,
      progressMessage: updatedJob.progressMessage,
      elapsedSeconds: (Date.now() - updatedJob.createdAt) / 1000,
    }

    // Include result when completed
    if (updatedJob.status === 'completed') {
      response.result = createMockResult(updatedJob.caseId)
    }

    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    })
  })
}

// Extend base test to include API mocking
export const test = base.extend({
  // Auto-mock API routes for every test
  page: async ({ page }, use) => {
    await setupApiMocks(page)
    await use(page)
  },
})

export { expect }
