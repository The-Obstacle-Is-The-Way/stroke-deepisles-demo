import { http, HttpResponse, delay } from "msw";
import type { JobStatus } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:7860";

// In-memory job store for mocking
interface MockJob {
  id: string;
  caseId: string;
  status: JobStatus;
  progress: number;
  progressMessage: string;
  elapsedSeconds: number;
  fastMode: boolean;
  createdAt: number;
}

const mockJobs = new Map<string, MockJob>();
let jobCounter = 0;

// Configurable job duration for tests (ms)
// Default: 500ms for fast tests
let mockJobDurationMs = 500;

/**
 * Set the mock job duration for tests.
 * Jobs will complete after this many milliseconds.
 */
export function setMockJobDuration(durationMs: number): void {
  mockJobDurationMs = durationMs;
}

// Simulate job progression over time
function getJobProgress(job: MockJob): MockJob {
  const elapsed = (Date.now() - job.createdAt) / 1000;
  const duration = mockJobDurationMs / 1000; // Convert to seconds

  if (job.status === "completed" || job.status === "failed") {
    return job;
  }

  // Progress through stages based on elapsed time relative to configured duration
  // Stages: 20% loading, 40% inference, 30% processing, 10% finalizing
  const progress20 = duration * 0.2;
  const progress60 = duration * 0.6;
  const progress90 = duration * 0.9;

  if (elapsed < progress20) {
    return {
      ...job,
      status: "running",
      progress: 10,
      progressMessage: "Loading case data...",
      elapsedSeconds: elapsed,
    };
  } else if (elapsed < progress60) {
    return {
      ...job,
      status: "running",
      progress: 30,
      progressMessage: "Running DeepISLES inference...",
      elapsedSeconds: elapsed,
    };
  } else if (elapsed < progress90) {
    return {
      ...job,
      status: "running",
      progress: 70,
      progressMessage: "Processing results...",
      elapsedSeconds: elapsed,
    };
  } else if (elapsed < duration) {
    return {
      ...job,
      status: "running",
      progress: 90,
      progressMessage: "Computing metrics...",
      elapsedSeconds: elapsed,
    };
  } else {
    // Job complete
    return {
      ...job,
      status: "completed",
      progress: 100,
      progressMessage: "Segmentation complete",
      elapsedSeconds: elapsed,
    };
  }
}

export const handlers = [
  // GET /api/cases - List available cases
  http.get(`${API_BASE}/api/cases`, async () => {
    await delay(100);
    return HttpResponse.json({
      cases: ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"],
    });
  }),

  // POST /api/segment - Create segmentation job (returns immediately)
  http.post(`${API_BASE}/api/segment`, async ({ request }) => {
    const body = (await request.json()) as {
      case_id: string;
      fast_mode?: boolean;
    };
    await delay(50); // Small delay to simulate network

    // Create a new job
    const jobId = `mock-${++jobCounter}`;
    const job: MockJob = {
      id: jobId,
      caseId: body.case_id,
      status: "pending",
      progress: 0,
      progressMessage: "Job queued",
      elapsedSeconds: 0,
      fastMode: body.fast_mode !== false,
      createdAt: Date.now(),
    };
    mockJobs.set(jobId, job);

    // Return 202 Accepted with job ID
    return HttpResponse.json(
      {
        jobId: jobId,
        status: "pending",
        message: `Segmentation job queued for ${body.case_id}`,
      },
      { status: 202 },
    );
  }),

  // GET /api/jobs/:jobId - Get job status
  http.get(`${API_BASE}/api/jobs/:jobId`, async ({ params }) => {
    const jobId = params.jobId as string;
    await delay(50); // Small delay to simulate network

    const job = mockJobs.get(jobId);
    if (!job) {
      return HttpResponse.json(
        { detail: `Job not found: ${jobId}. Jobs expire after 1 hour.` },
        { status: 404 },
      );
    }

    // Update job progress based on elapsed time
    const updatedJob = getJobProgress(job);
    mockJobs.set(jobId, updatedJob);

    // Build response
    const response: Record<string, unknown> = {
      jobId: updatedJob.id,
      status: updatedJob.status,
      progress: updatedJob.progress,
      progressMessage: updatedJob.progressMessage,
      elapsedSeconds: Math.round(updatedJob.elapsedSeconds * 100) / 100,
    };

    // Include result if completed
    if (updatedJob.status === "completed") {
      // Filenames must match actual backend output format
      response.result = {
        caseId: updatedJob.caseId,
        diceScore: 0.847,
        volumeMl: 15.32,
        elapsedSeconds: updatedJob.fastMode ? 12.5 : 45.0,
        dwiUrl: `${API_BASE}/files/${jobId}/${updatedJob.caseId}/${updatedJob.caseId}_dwi.nii.gz`,
        predictionUrl: `${API_BASE}/files/${jobId}/${updatedJob.caseId}/lesion_msk.nii.gz`,
      };
    }

    return HttpResponse.json(response);
  }),
];

// Track retry attempts for cold-start testing
let casesAttempts = 0;

/** Reset the cases attempt counter (call in test beforeEach) */
export function resetCasesAttempts(): void {
  casesAttempts = 0;
}

// Error handlers for testing error states
export const errorHandlers = {
  casesServerError: http.get(`${API_BASE}/api/cases`, () => {
    return HttpResponse.json(
      { detail: "Internal server error" },
      { status: 500 },
    );
  }),

  casesNetworkError: http.get(`${API_BASE}/api/cases`, () => {
    return HttpResponse.error();
  }),

  // 503 on first attempt, success on retry (tests cold-start retry)
  casesColdStart: http.get(`${API_BASE}/api/cases`, async () => {
    casesAttempts++;
    if (casesAttempts === 1) {
      return HttpResponse.json(
        { detail: "Service Unavailable" },
        { status: 503 },
      );
    }
    // Succeed on retry
    return HttpResponse.json({
      cases: ["sub-stroke0001", "sub-stroke0002", "sub-stroke0003"],
    });
  }),

  segmentCreateError: http.post(`${API_BASE}/api/segment`, () => {
    return HttpResponse.json(
      { detail: "Failed to create job: case not found" },
      { status: 400 },
    );
  }),

  jobNotFound: http.get(`${API_BASE}/api/jobs/:jobId`, () => {
    return HttpResponse.json(
      { detail: "Job not found or expired" },
      { status: 404 },
    );
  }),

  // Simulate a job that fails during processing
  jobFailed: [
    http.post(`${API_BASE}/api/segment`, async ({ request }) => {
      const body = (await request.json()) as { case_id: string };
      const jobId = `fail-${++jobCounter}`;
      mockJobs.set(jobId, {
        id: jobId,
        caseId: body.case_id,
        status: "failed",
        progress: 30,
        progressMessage: "Error occurred",
        elapsedSeconds: 5.2,
        fastMode: true,
        createdAt: Date.now(),
      });
      return HttpResponse.json(
        { jobId, status: "pending", message: "Job queued" },
        { status: 202 },
      );
    }),
    http.get(`${API_BASE}/api/jobs/:jobId`, ({ params }) => {
      const jobId = params.jobId as string;
      const job = mockJobs.get(jobId);
      if (!job) {
        return HttpResponse.json({ detail: "Not found" }, { status: 404 });
      }
      return HttpResponse.json({
        jobId: job.id,
        status: "failed",
        progress: 30,
        progressMessage: "Error occurred",
        elapsedSeconds: 5.2,
        error: "Segmentation failed: out of memory",
      });
    }),
  ],
};
