import type {
  CasesResponse,
  CreateJobResponse,
  JobStatusResponse,
} from "../types";

/**
 * Safely parse JSON error response, logging failures in development.
 * Returns empty object if parsing fails (e.g., HTML error pages from proxies).
 * (BUG-013 fix: was silently returning {} without any logging)
 */
async function parseErrorJson(
  response: Response,
): Promise<{ detail?: string }> {
  try {
    return await response.json();
  } catch (parseError) {
    // Log in development to help debug malformed responses
    if (import.meta.env.DEV) {
      console.warn(
        "Failed to parse error response as JSON:",
        parseError,
        "Status:",
        response.status,
        response.statusText,
      );
    }
    return {};
  }
}

function getApiBase(): string {
  const url = import.meta.env.VITE_API_URL;

  // In production, VITE_API_URL must be set - fail fast with clear error
  if (import.meta.env.PROD && !url) {
    throw new Error(
      "VITE_API_URL environment variable is required in production. " +
        "Set it to the backend API URL (e.g., https://your-app.hf.space).",
    );
  }

  // In development, fall back to localhost
  return url || "http://localhost:7860";
}

const API_BASE = getApiBase();

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get list of available cases
   */
  async getCases(signal?: AbortSignal): Promise<CasesResponse> {
    const response = await fetch(`${this.baseUrl}/api/cases`, { signal });

    if (!response.ok) {
      const error = await parseErrorJson(response);
      throw new ApiError(
        `Failed to fetch cases: ${response.statusText}`,
        response.status,
        error.detail,
      );
    }

    return response.json();
  }

  /**
   * Create a segmentation job (async - returns immediately with job ID)
   *
   * The actual ML inference runs in the background. Poll getJobStatus()
   * to track progress and retrieve results when complete.
   */
  async createSegmentJob(
    caseId: string,
    fastMode: boolean = true,
    signal?: AbortSignal,
  ): Promise<CreateJobResponse> {
    const response = await fetch(`${this.baseUrl}/api/segment`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        case_id: caseId,
        fast_mode: fastMode,
      }),
      signal,
    });

    if (!response.ok) {
      const error = await parseErrorJson(response);
      throw new ApiError(
        `Failed to create job: ${error.detail || response.statusText}`,
        response.status,
        error.detail,
      );
    }

    return response.json();
  }

  /**
   * Get the status of a segmentation job
   *
   * Poll this endpoint to track progress and retrieve results.
   * When status is 'completed', the result field contains segmentation data.
   * When status is 'failed', the error field contains the error message.
   */
  async getJobStatus(
    jobId: string,
    signal?: AbortSignal,
  ): Promise<JobStatusResponse> {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}`, {
      signal,
    });

    if (response.status === 404) {
      throw new ApiError(
        "Job not found or expired",
        404,
        "Jobs expire after 1 hour",
      );
    }

    if (!response.ok) {
      const error = await parseErrorJson(response);
      throw new ApiError(
        `Failed to get job status: ${error.detail || response.statusText}`,
        response.status,
        error.detail,
      );
    }

    return response.json();
  }
}

export const apiClient = new ApiClient(API_BASE);
