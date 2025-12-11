import { useState, useCallback, useRef } from 'react'
import { apiClient } from '../api/client'
import type { SegmentationResult } from '../types'

export function useSegmentation() {
  const [result, setResult] = useState<SegmentationResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Track the current request to prevent race conditions
  // Each new request gets a unique token; only the latest request's results are applied
  const currentRequestRef = useRef<number>(0)
  const abortControllerRef = useRef<AbortController | null>(null)

  const runSegmentation = useCallback(async (caseId: string, fastMode = true) => {
    // Cancel any in-flight request
    abortControllerRef.current?.abort()
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    // Increment request token to track this request
    const requestToken = ++currentRequestRef.current

    setIsLoading(true)
    setError(null)

    try {
      const data = await apiClient.runSegmentation(caseId, fastMode, abortController.signal)

      // Only apply results if this is still the current request
      // Prevents stale responses from overwriting newer results
      if (requestToken !== currentRequestRef.current) return

      setResult({
        dwiUrl: data.dwiUrl,
        predictionUrl: data.predictionUrl,
        metrics: {
          caseId: data.caseId,
          diceScore: data.diceScore,
          volumeMl: data.volumeMl,
          elapsedSeconds: data.elapsedSeconds,
        },
      })
    } catch (err) {
      // Ignore abort errors - user intentionally cancelled
      if (err instanceof Error && err.name === 'AbortError') return

      // Only apply error if this is still the current request
      if (requestToken !== currentRequestRef.current) return

      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      setResult(null)
    } finally {
      // Only clear loading if this is still the current request
      if (requestToken === currentRequestRef.current) {
        setIsLoading(false)
      }
    }
  }, [])

  return { result, isLoading, error, runSegmentation }
}
