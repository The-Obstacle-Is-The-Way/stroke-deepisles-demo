import type { CasesResponse, SegmentResponse } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:7860'

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

  async getCases(): Promise<CasesResponse> {
    const response = await fetch(`${this.baseUrl}/api/cases`)

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
    fastMode: boolean = true
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
