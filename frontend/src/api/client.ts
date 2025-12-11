import type { CasesResponse, SegmentResponse } from '../types'

function getApiBase(): string {
  const url = import.meta.env.VITE_API_URL

  // In production, VITE_API_URL must be set - fail fast with clear error
  if (import.meta.env.PROD && !url) {
    throw new Error(
      'VITE_API_URL environment variable is required in production. ' +
        'Set it to the backend API URL (e.g., https://your-app.hf.space).'
    )
  }

  // In development, fall back to localhost
  return url || 'http://localhost:7860'
}

const API_BASE = getApiBase()

export class ApiError extends Error {
  status: number
  detail?: string

  constructor(message: string, status: number, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async getCases(signal?: AbortSignal): Promise<CasesResponse> {
    const response = await fetch(`${this.baseUrl}/api/cases`, { signal })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(
        `Failed to fetch cases: ${response.statusText}`,
        response.status,
        error.detail
      )
    }

    return response.json()
  }

  async runSegmentation(
    caseId: string,
    fastMode: boolean = true,
    signal?: AbortSignal
  ): Promise<SegmentResponse> {
    const response = await fetch(`${this.baseUrl}/api/segment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        case_id: caseId,
        fast_mode: fastMode,
      }),
      signal,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(
        `Segmentation failed: ${error.detail || response.statusText}`,
        response.status,
        error.detail
      )
    }

    return response.json()
  }
}

export const apiClient = new ApiClient(API_BASE)
