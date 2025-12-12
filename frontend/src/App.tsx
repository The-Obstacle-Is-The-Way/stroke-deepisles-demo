import { useState } from 'react'
import { Layout } from './components/Layout'
import { CaseSelector } from './components/CaseSelector'
import { NiiVueViewer } from './components/NiiVueViewer'
import { MetricsPanel } from './components/MetricsPanel'
import { ProgressIndicator } from './components/ProgressIndicator'
import { useSegmentation } from './hooks/useSegmentation'

export default function App() {
  const [selectedCase, setSelectedCase] = useState<string | null>(null)
  const {
    result,
    isLoading,
    error,
    jobStatus,
    progress,
    progressMessage,
    elapsedSeconds,
    runSegmentation,
    cancelJob,
  } = useSegmentation()

  const handleRunSegmentation = async () => {
    if (selectedCase) {
      await runSegmentation(selectedCase)
    }
  }

  // Show progress indicator when job is active
  const showProgress = isLoading && jobStatus && jobStatus !== 'completed'

  return (
    <Layout>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel: Controls */}
        <div className="space-y-4">
          <CaseSelector
            selectedCase={selectedCase}
            onSelectCase={setSelectedCase}
          />

          <button
            onClick={handleRunSegmentation}
            disabled={!selectedCase || isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600
                       disabled:cursor-not-allowed text-white font-medium
                       py-3 px-4 rounded-lg transition-colors"
          >
            {isLoading ? 'Processing...' : 'Run Segmentation'}
          </button>

          {/* Cancel button when processing */}
          {isLoading && (
            <button
              onClick={cancelJob}
              className="w-full bg-gray-700 hover:bg-gray-600 text-gray-300
                         font-medium py-2 px-4 rounded-lg transition-colors text-sm"
            >
              Cancel
            </button>
          )}

          {/* Progress indicator */}
          {showProgress && (
            <ProgressIndicator
              progress={progress}
              message={progressMessage}
              status={jobStatus}
              elapsedSeconds={elapsedSeconds}
            />
          )}

          {/* Error display */}
          {error && !isLoading && (
            <div
              role="alert"
              className="bg-red-900/50 text-red-300 p-3 rounded-lg text-sm"
            >
              <p className="font-medium">Error</p>
              <p className="mt-1">{error}</p>
            </div>
          )}

          {/* Results metrics */}
          {result && <MetricsPanel metrics={result.metrics} />}
        </div>

        {/* Right Panel: Viewer */}
        <div className="lg:col-span-2">
          {result ? (
            <NiiVueViewer
              backgroundUrl={result.dwiUrl}
              overlayUrl={result.predictionUrl}
            />
          ) : (
            <div className="bg-gray-900 rounded-lg h-[500px] flex items-center justify-center">
              <p className="text-gray-400">
                {isLoading
                  ? 'Processing segmentation...'
                  : 'Select a case and run segmentation to view results'}
              </p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
