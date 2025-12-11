import { useState } from 'react'
import { Layout } from './components/Layout'
import { CaseSelector } from './components/CaseSelector'
import { NiiVueViewer } from './components/NiiVueViewer'
import { MetricsPanel } from './components/MetricsPanel'
import { useSegmentation } from './hooks/useSegmentation'

export default function App() {
  const [selectedCase, setSelectedCase] = useState<string | null>(null)
  const { result, isLoading, error, runSegmentation } = useSegmentation()

  const handleRunSegmentation = async () => {
    if (selectedCase) {
      await runSegmentation(selectedCase)
    }
  }

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

          {error && (
            <div role="alert" className="bg-red-900/50 text-red-300 p-3 rounded-lg">
              {error}
            </div>
          )}

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
                Select a case and run segmentation to view results
              </p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
