import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { server } from '../../mocks/server'
import { errorHandlers } from '../../mocks/handlers'
import { useSegmentation } from '../useSegmentation'

describe('useSegmentation', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts with null result and not loading', () => {
    const { result } = renderHook(() => useSegmentation())

    expect(result.current.result).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.jobStatus).toBeNull()
  })

  it('sets loading state and job status during segmentation', async () => {
    const { result } = renderHook(() => useSegmentation())

    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.isLoading).toBe(true)

    // Wait for job to be created
    await waitFor(() => {
      expect(result.current.jobId).toBeDefined()
    })

    expect(result.current.jobStatus).toBeDefined()
  })

  it('returns result on job completion', async () => {
    const { result } = renderHook(() => useSegmentation())

    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    // Wait for job creation
    await waitFor(() => {
      expect(result.current.jobId).toBeDefined()
    })

    // Advance time to allow job to complete (mock jobs complete in ~3s)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.result).not.toBeNull()
    })

    expect(result.current.result?.metrics.caseId).toBe('sub-stroke0001')
    expect(result.current.result?.metrics.diceScore).toBe(0.847)
    expect(result.current.result?.dwiUrl).toContain('dwi.nii.gz')
  })

  it('shows progress updates during job execution', async () => {
    const { result } = renderHook(() => useSegmentation())

    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    // Wait for job to start
    await waitFor(() => {
      expect(result.current.jobId).toBeDefined()
    })

    // Progress should be tracked
    expect(result.current.progress).toBeGreaterThanOrEqual(0)
    expect(result.current.progressMessage).toBeDefined()
  })

  it('sets error on job creation failure', async () => {
    server.use(errorHandlers.segmentCreateError)

    const { result } = renderHook(() => useSegmentation())

    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.error).toMatch(/failed to create job/i)
    expect(result.current.result).toBeNull()
  })

  it('clears previous error on new request', async () => {
    server.use(errorHandlers.segmentCreateError)
    const { result } = renderHook(() => useSegmentation())

    // First request fails
    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    await waitFor(() => {
      expect(result.current.error).not.toBeNull()
    })

    // Reset to success handler
    server.resetHandlers()

    // Second request should clear error
    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.error).toBeNull()
    expect(result.current.isLoading).toBe(true)
  })

  it('can cancel a running job', async () => {
    const { result } = renderHook(() => useSegmentation())

    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(true)
    })

    // Cancel the job
    act(() => {
      result.current.cancelJob()
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.jobStatus).toBeNull()
  })

  it('cleans up polling on unmount', async () => {
    const { result, unmount } = renderHook(() => useSegmentation())

    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(true)
    })

    // Unmount should not throw
    unmount()
  })
})
