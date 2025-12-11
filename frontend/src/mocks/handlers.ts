import { http, HttpResponse, delay } from 'msw'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:7860'

export const handlers = [
  http.get(`${API_BASE}/api/cases`, async () => {
    await delay(100)
    return HttpResponse.json({
      cases: ['sub-stroke0001', 'sub-stroke0002', 'sub-stroke0003'],
    })
  }),

  http.post(`${API_BASE}/api/segment`, async ({ request }) => {
    const body = (await request.json()) as { case_id: string; fast_mode?: boolean }
    await delay(200)
    return HttpResponse.json({
      caseId: body.case_id,
      diceScore: 0.847,
      volumeMl: 15.32,
      // Reflect fast_mode in response - slower when fast_mode=false
      elapsedSeconds: body.fast_mode === false ? 45.0 : 12.5,
      dwiUrl: `${API_BASE}/files/dwi.nii.gz`,
      predictionUrl: `${API_BASE}/files/prediction.nii.gz`,
    })
  }),
]

// Error handlers for testing error states
export const errorHandlers = {
  casesServerError: http.get(`${API_BASE}/api/cases`, () => {
    return HttpResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }),

  casesNetworkError: http.get(`${API_BASE}/api/cases`, () => {
    return HttpResponse.error()
  }),

  segmentServerError: http.post(`${API_BASE}/api/segment`, () => {
    return HttpResponse.json(
      { detail: 'Segmentation failed: out of memory' },
      { status: 500 }
    )
  }),

  segmentTimeout: http.post(`${API_BASE}/api/segment`, async () => {
    await delay(30000)
    return HttpResponse.json({ detail: 'Timeout' }, { status: 504 })
  }),
}
