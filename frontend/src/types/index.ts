// Segmentation metrics
export interface Metrics {
  caseId: string;
  diceScore: number | null;
  volumeMl: number | null;
  elapsedSeconds: number;
  warning?: string | null;
}

// Final segmentation result with URLs and metrics
export interface SegmentationResult {
  dwiUrl: string;
  predictionUrl: string;
  metrics: Metrics;
}

// API Response Types
export interface CasesResponse {
  cases: string[];
}

// Segmentation result data (embedded in job response)
export interface SegmentResponse {
  caseId: string;
  diceScore: number | null;
  volumeMl: number | null;
  elapsedSeconds: number;
  dwiUrl: string;
  predictionUrl: string;
  warning?: string | null;
}

// Backend Job Status Types (returned by API - never includes 'waking_up')
export type BackendJobStatus = "pending" | "running" | "completed" | "failed";

// Frontend Job Status Types (includes client-side states like 'waking_up')
export type JobStatus = BackendJobStatus | "waking_up";

// Response from POST /api/segment (job creation)
export interface CreateJobResponse {
  jobId: string;
  status: BackendJobStatus; // Backend never returns 'waking_up'
  message: string;
}

// Response from GET /api/jobs/{jobId} (status polling)
export interface JobStatusResponse {
  jobId: string;
  status: BackendJobStatus; // Backend never returns 'waking_up'
  progress: number;
  progressMessage: string;
  elapsedSeconds?: number;
  result?: SegmentResponse;
  error?: string;
}
