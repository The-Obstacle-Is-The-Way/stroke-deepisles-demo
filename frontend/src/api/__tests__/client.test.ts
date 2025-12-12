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

  describe('createSegmentJob', () => {
    it('returns job ID and pending status', async () => {
      const result = await apiClient.createSegmentJob('sub-stroke0001')

      expect(result.jobId).toBeDefined()
      expect(result.status).toBe('pending')
      expect(result.message).toContain('sub-stroke0001')
    })

    it('sends fast_mode parameter', async () => {
      const result = await apiClient.createSegmentJob('sub-stroke0001', false)

      expect(result.jobId).toBeDefined()
      expect(result.status).toBe('pending')
    })

    it('throws ApiError on server error', async () => {
      server.use(errorHandlers.segmentCreateError)

      await expect(
        apiClient.createSegmentJob('sub-stroke0001')
      ).rejects.toThrow(/failed to create job/i)
    })
  })

  describe('getJobStatus', () => {
    it('returns job status with progress', async () => {
      // First create a job
      const createResult = await apiClient.createSegmentJob('sub-stroke0001')

      // Then get its status
      const status = await apiClient.getJobStatus(createResult.jobId)

      expect(status.jobId).toBe(createResult.jobId)
      expect(['pending', 'running', 'completed']).toContain(status.status)
      expect(status.progress).toBeGreaterThanOrEqual(0)
      expect(status.progress).toBeLessThanOrEqual(100)
      expect(status.progressMessage).toBeDefined()
    })

    it('throws ApiError when job not found', async () => {
      server.use(errorHandlers.jobNotFound)

      await expect(
        apiClient.getJobStatus('nonexistent-job')
      ).rejects.toThrow(/not found/i)
    })
  })
})
