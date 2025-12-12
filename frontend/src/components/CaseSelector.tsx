import { useEffect, useState } from "react";
import { apiClient, ApiError } from "../api/client";

// Cold start retry configuration (matches useSegmentation.ts)
const MAX_COLD_START_RETRIES = 5;
const INITIAL_RETRY_DELAY = 2000;
const MAX_RETRY_DELAY = 30000;

interface CaseSelectorProps {
  selectedCase: string | null;
  onSelectCase: (caseId: string) => void;
}

export function CaseSelector({
  selectedCase,
  onSelectCase,
}: CaseSelectorProps) {
  const [cases, setCases] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isWakingUp, setIsWakingUp] = useState(false);

  // Fetch cases on mount with cold-start retry logic
  // Using inline async function pattern recommended by React docs for data fetching
  useEffect(() => {
    let isActive = true;
    const abortController = new AbortController();

    async function fetchCases() {
      let attempts = 0;

      while (attempts <= MAX_COLD_START_RETRIES && isActive) {
        try {
          const data = await apiClient.getCases(abortController.signal);
          if (!isActive) return;
          setCases(data.cases);
          setIsWakingUp(false);
          setRetryCount(0);
          setIsLoading(false);
          return; // Success
        } catch (err) {
          if (!isActive) return;
          if (err instanceof Error && err.name === "AbortError") return;

          const is503 = err instanceof ApiError && err.status === 503;
          const isNetworkError =
            err instanceof TypeError &&
            err.message.toLowerCase().includes("fetch");

          // Retry on cold start (503) or network errors
          if ((is503 || isNetworkError) && attempts < MAX_COLD_START_RETRIES) {
            attempts++;
            setRetryCount(attempts);
            setIsWakingUp(true);

            // Exponential backoff
            const delay = Math.min(
              INITIAL_RETRY_DELAY * Math.pow(2, attempts - 1),
              MAX_RETRY_DELAY,
            );
            await new Promise((resolve) => setTimeout(resolve, delay));
            continue;
          }

          // Max retries exceeded or non-retryable error
          const message =
            is503 || isNetworkError
              ? "Backend failed to wake up. Please refresh the page."
              : err instanceof Error
                ? err.message
                : "Unknown error";
          setError(`Failed to load cases: ${message}`);
          setIsWakingUp(false);
          setIsLoading(false);
          return;
        }
      }
    }

    fetchCases();

    return () => {
      isActive = false;
      abortController.abort();
    };
  }, []);

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4">
        {isWakingUp ? (
          <p className="text-yellow-400">
            Backend waking up... Retry {retryCount}/{MAX_COLD_START_RETRIES}
          </p>
        ) : (
          <p className="text-gray-400">Loading cases...</p>
        )}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/50 rounded-lg p-4">
        <p className="text-red-300">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <label className="block text-sm font-medium mb-2">Select Case</label>
      <select
        value={selectedCase || ""}
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
  );
}
