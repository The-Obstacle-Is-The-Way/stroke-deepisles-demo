import type { JobStatus } from '../types'

interface ProgressIndicatorProps {
  progress: number
  message: string
  status: JobStatus
  elapsedSeconds?: number
}

/**
 * Visual progress indicator for long-running ML inference jobs.
 *
 * Shows:
 * - Progress bar with percentage
 * - Current operation message
 * - Elapsed time
 * - Status-appropriate coloring (blue for running, red for failed)
 */
export function ProgressIndicator({
  progress,
  message,
  status,
  elapsedSeconds,
}: ProgressIndicatorProps) {
  const isError = status === 'failed'
  const isComplete = status === 'completed'
  const isWakingUp = status === 'waking_up'

  // Determine bar color based on status
  const barColorClass = isError
    ? 'bg-red-500'
    : isComplete
      ? 'bg-green-500'
      : isWakingUp
        ? 'bg-yellow-500'
        : 'bg-blue-500'

  // Animate the bar while running or waking up
  const animationClass =
    status === 'running' || status === 'pending' || status === 'waking_up'
      ? 'animate-pulse'
      : ''

  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-3">
      {/* Header with message and percentage */}
      <div className="flex justify-between items-center text-sm">
        <span className="text-gray-300 font-medium">{message}</span>
        <span className="text-gray-400 tabular-nums">{progress}%</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-700 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${barColorClass} ${animationClass}`}
          style={{ width: `${progress}%` }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={message}
        />
      </div>

      {/* Footer with elapsed time and status */}
      <div className="flex justify-between items-center text-xs text-gray-500">
        {elapsedSeconds !== undefined ? (
          <span className="tabular-nums">
            Elapsed: {elapsedSeconds.toFixed(1)}s
          </span>
        ) : (
          <span>Starting...</span>
        )}

        <span
          className={`capitalize ${
            isError
              ? 'text-red-400'
              : isComplete
                ? 'text-green-400'
                : isWakingUp
                  ? 'text-yellow-400'
                  : 'text-blue-400'
          }`}
        >
          {status === 'waking_up' ? 'waking up' : status}
        </span>
      </div>
    </div>
  )
}
