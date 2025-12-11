export interface Metrics {
  caseId: string
  diceScore: number | null
  volumeMl: number | null
  elapsedSeconds: number
}

export interface SegmentationResult {
  dwiUrl: string
  predictionUrl: string
  metrics: Metrics
}

export interface CasesResponse {
  cases: string[]
}

export interface SegmentResponse {
  caseId: string
  diceScore: number | null
  volumeMl: number | null
  elapsedSeconds: number
  dwiUrl: string
  predictionUrl: string
}
