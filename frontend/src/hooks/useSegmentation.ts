import { useState, useCallback } from 'react'
import { apiClient } from '../api/client'
import type { SegmentationResult } from '../types'

export function useSegmentation() {
  const [result, setResult] = useState<SegmentationResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runSegmentation = useCallback(async (caseId: string, fastMode = true) => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await apiClient.runSegmentation(caseId, fastMode)

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
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      setResult(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return { result, isLoading, error, runSegmentation }
}
