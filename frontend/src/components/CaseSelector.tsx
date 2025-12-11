import { useEffect, useState } from 'react'
import { apiClient } from '../api/client'

interface CaseSelectorProps {
  selectedCase: string | null
  onSelectCase: (caseId: string) => void
}

export function CaseSelector({ selectedCase, onSelectCase }: CaseSelectorProps) {
  const [cases, setCases] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await apiClient.getCases()
        setCases(data.cases)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error'
        setError(`Failed to load cases: ${message}`)
      } finally {
        setIsLoading(false)
      }
    }

    fetchCases()
  }, [])

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        <p className="text-gray-400">Loading cases...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/50 rounded-lg p-4">
        <p className="text-red-300">{error}</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <label className="block text-sm font-medium mb-2">Select Case</label>
      <select
        value={selectedCase || ''}
        onChange={(e) => onSelectCase(e.target.value)}
        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2
                   text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        <option value="">Choose a case...</option>
        {cases.map((caseId) => (
          <option key={caseId} value={caseId}>
            {caseId}
          </option>
        ))}
      </select>
    </div>
  )
}
