import type { Metrics } from '../types'

interface MetricsPanelProps {
  metrics: Metrics
}

export function MetricsPanel({ metrics }: MetricsPanelProps) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-3">
      <h3 className="font-medium text-lg">Results</h3>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-400">Case:</span>
          <span className="ml-2 font-mono">{metrics.caseId}</span>
        </div>

        {metrics.diceScore !== null && (
          <div>
            <span className="text-gray-400">Dice Score:</span>
            <span className="ml-2 font-mono text-green-400">
              {metrics.diceScore.toFixed(3)}
            </span>
          </div>
        )}

        {metrics.volumeMl !== null && (
          <div>
            <span className="text-gray-400">Volume:</span>
            <span className="ml-2 font-mono">
              {metrics.volumeMl.toFixed(2)} mL
            </span>
          </div>
        )}

        <div>
          <span className="text-gray-400">Time:</span>
          <span className="ml-2 font-mono">
            {metrics.elapsedSeconds.toFixed(1)}s
          </span>
        </div>
      </div>
    </div>
  )
}
