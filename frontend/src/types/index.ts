// Segmentation metrics
export interface Metrics {
  caseId: string
  diceScore: number | null
  volumeMl: number | null
  elapsedSeconds: number
}

// Final segmentation result with URLs and metrics
export interface SegmentationResult {
  dwiUrl: string
  predictionUrl: string
  metrics: Metrics
}

// API Response Types
export interface CasesResponse {
  cases: string[]
}

// Segmentation result data (embedded in job response)
export interface SegmentResponse {
  caseId: string
  diceScore: number | null
  volumeMl: number | null
  elapsedSeconds: number
  dwiUrl: string
  predictionUrl: string
}

// Job Status Types
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'

// Response from POST /api/segment (job creation)
export interface CreateJobResponse {
  jobId: string
  status: JobStatus
  message: string
}

// Response from GET /api/jobs/{jobId} (status polling)
export interface JobStatusResponse {
  jobId: string
  status: JobStatus
  progress: number
  progressMessage: string
  elapsedSeconds?: number
  result?: SegmentResponse
  error?: string
}
