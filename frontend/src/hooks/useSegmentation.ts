import { useState, useCallback, useRef, useEffect } from 'react'
import { apiClient, ApiError } from '../api/client'
import type { SegmentationResult, JobStatus } from '../types'

// Polling interval in milliseconds
const POLLING_INTERVAL = 2000

// Cold start retry configuration
const MAX_COLD_START_RETRIES = 5
const INITIAL_RETRY_DELAY = 2000 // 2 seconds
const MAX_RETRY_DELAY = 30000 // 30 seconds

/**
 * Sleep utility for async delays
 */
const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Hook for running segmentation with async job polling.
 *
 * Instead of waiting for the full inference to complete (which can timeout
 * on HuggingFace Spaces), this hook:
 * 1. Creates a job that returns immediately with a job ID
 * 2. Polls for job status/progress every 2 seconds
 * 3. Returns results when the job completes
 *
 * This avoids the ~60s gateway timeout on HF Spaces while providing
 * real-time progress updates to the user.
 */
export function useSegmentation() {
  // Result state
  const [result, setResult] = useState<SegmentationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Job tracking state
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [elapsedSeconds, setElapsedSeconds] = useState<number | undefined>(
    undefined
  )

  // Loading state - true from job creation until completion/failure
  const [isLoading, setIsLoading] = useState(false)

  // Refs for managing async operations
  const currentJobRef = useRef<string | null>(null)
  const pollingIntervalRef = useRef<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  /**
   * Stop polling for job status
   */
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
  }, [])

  /**
   * Poll for job status and update state
   */
  const pollJobStatus = useCallback(
    async (id: string, signal: AbortSignal) => {
      // Don't poll if this isn't the current job
      if (id !== currentJobRef.current) {
        stopPolling()
        return
      }

      try {
        const response = await apiClient.getJobStatus(id, signal)

        // Ignore results if job changed
        if (id !== currentJobRef.current) return

        // Update progress state
        setJobStatus(response.status)
        setProgress(response.progress)
        setProgressMessage(response.progressMessage)
        setElapsedSeconds(response.elapsedSeconds)

        // Handle completion
        if (response.status === 'completed' && response.result) {
          stopPolling()
          setIsLoading(false)
          setResult({
            dwiUrl: response.result.dwiUrl,
            predictionUrl: response.result.predictionUrl,
            metrics: {
              caseId: response.result.caseId,
              diceScore: response.result.diceScore,
              volumeMl: response.result.volumeMl,
              elapsedSeconds: response.result.elapsedSeconds,
              warning: response.result.warning,
            },
          })
        }

        // Handle failure
        if (response.status === 'failed') {
          stopPolling()
          setIsLoading(false)
          setError(response.error || 'Job failed')
          setResult(null)
        }
      } catch (err) {
        // Ignore abort errors
        if (err instanceof Error && err.name === 'AbortError') return

        // Don't stop polling on transient network errors - retry next interval
        console.warn('Polling error (will retry):', err)
      }
    },
    [stopPolling]
  )

  /**
   * Start segmentation job and begin polling
   *
   * @param caseId - The case ID to process
   * @param fastMode - Whether to use fast inference mode
   */
  const runSegmentation = useCallback(
    async (caseId: string, fastMode = true) => {
      // Cancel any existing job/polling
      stopPolling()
      abortControllerRef.current?.abort()

      const abortController = new AbortController()
      abortControllerRef.current = abortController

      // Reset state
      setError(null)
      setResult(null)
      setProgress(0)
      setProgressMessage('Creating job...')
      setJobStatus('pending')
      setElapsedSeconds(undefined)
      setIsLoading(true)

      // Retry loop for cold start handling (replaces recursive call)
      let retryCount = 0
      while (retryCount <= MAX_COLD_START_RETRIES) {
        try {
          // Create the job
          const response = await apiClient.createSegmentJob(
            caseId,
            fastMode,
            abortController.signal
          )

          // Store job reference
          const newJobId = response.jobId
          setJobId(newJobId)
          currentJobRef.current = newJobId
          setJobStatus(response.status)
          setProgressMessage(response.message)

          // Start polling
          pollingIntervalRef.current = window.setInterval(() => {
            pollJobStatus(newJobId, abortController.signal)
          }, POLLING_INTERVAL)

          // Do an initial poll immediately
          await pollJobStatus(newJobId, abortController.signal)

          // Success - exit retry loop
          return
        } catch (err) {
          // Ignore abort errors
          if (err instanceof Error && err.name === 'AbortError') return

          // Detect cold start (503 Service Unavailable or network failure)
          const is503 = err instanceof ApiError && err.status === 503
          const isNetworkError =
            err instanceof TypeError &&
            err.message.toLowerCase().includes('fetch')

          // Retry on cold start errors with exponential backoff
          if (
            (is503 || isNetworkError) &&
            retryCount < MAX_COLD_START_RETRIES
          ) {
            retryCount++
            setJobStatus('waking_up')
            setProgressMessage(
              `Backend is waking up... Please wait (~30-60s). Retry ${retryCount}/${MAX_COLD_START_RETRIES}`
            )
            setProgress(0)

            // Exponential backoff: 2s, 4s, 8s, 16s, 30s (capped)
            const delay = Math.min(
              INITIAL_RETRY_DELAY * Math.pow(2, retryCount - 1),
              MAX_RETRY_DELAY
            )
            await sleep(delay)

            // Continue to next iteration of retry loop
            continue
          }

          // Max retries exceeded or non-retryable error
          const message =
            is503 || isNetworkError
              ? 'Backend failed to wake up. Please try again later.'
              : err instanceof Error
                ? err.message
                : 'Failed to start job'
          setError(message)
          setIsLoading(false)
          setJobStatus('failed')
          return
        }
      }
    },
    [pollJobStatus, stopPolling]
  )

  /**
   * Cancel the current job (stops polling, clears loading state)
   */
  const cancelJob = useCallback(() => {
    stopPolling()
    abortControllerRef.current?.abort()
    currentJobRef.current = null
    setIsLoading(false)
    setJobStatus(null)
    setProgress(0)
    setProgressMessage('')
  }, [stopPolling])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling()
      abortControllerRef.current?.abort()
    }
  }, [stopPolling])

  return {
    // Result data
    result,
    error,

    // Job status
    jobId,
    jobStatus,
    progress,
    progressMessage,
    elapsedSeconds,

    // Loading state
    isLoading,

    // Actions
    runSegmentation,
    cancelJob,
  }
}
