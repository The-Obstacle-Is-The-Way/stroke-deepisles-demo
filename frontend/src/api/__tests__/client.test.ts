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
