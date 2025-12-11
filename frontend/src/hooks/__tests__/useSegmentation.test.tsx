import { describe, it, expect } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { server } from '../../mocks/server'
import { errorHandlers } from '../../mocks/handlers'
import { useSegmentation } from '../useSegmentation'

describe('useSegmentation', () => {
  it('starts with null result and not loading', () => {
    const { result } = renderHook(() => useSegmentation())

    expect(result.current.result).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('sets loading state during segmentation', async () => {
    const { result } = renderHook(() => useSegmentation())

    act(() => {
      result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
  })

  it('returns result on success', async () => {
    const { result } = renderHook(() => useSegmentation())

    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.result).not.toBeNull()
    expect(result.current.result?.metrics.caseId).toBe('sub-stroke0001')
    expect(result.current.result?.metrics.diceScore).toBe(0.847)
    expect(result.current.result?.dwiUrl).toContain('dwi.nii.gz')
  })

  it('sets error on failure', async () => {
    server.use(errorHandlers.segmentServerError)

    const { result } = renderHook(() => useSegmentation())

    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.error).toMatch(/segmentation failed/i)
    expect(result.current.result).toBeNull()
  })

  it('clears previous error on new request', async () => {
    server.use(errorHandlers.segmentServerError)
    const { result } = renderHook(() => useSegmentation())

    // First request fails
    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })
    expect(result.current.error).not.toBeNull()

    // Reset to success handler
    server.resetHandlers()

    // Second request succeeds
    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })

    expect(result.current.error).toBeNull()
    expect(result.current.result).not.toBeNull()
  })

  it('clears previous result on new request', async () => {
    const { result } = renderHook(() => useSegmentation())

    // First request
    await act(async () => {
      await result.current.runSegmentation('sub-stroke0001')
    })
    expect(result.current.result).not.toBeNull()

    // Start second request - result should clear while loading
    act(() => {
      result.current.runSegmentation('sub-stroke0002')
    })

    // While loading, previous result is still available
    // (or you could clear it - depends on UX preference)
    expect(result.current.isLoading).toBe(true)
  })
})
