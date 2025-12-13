# Async Job Queue for Long-Running ML Inference

**Status**: APPROVED
**Created**: 2025-12-12
**Author**: Claude Code Audit

---

## Executive Summary

HuggingFace Spaces has a ~60-second gateway timeout that cannot be bypassed through
configuration. DeepISLES ML inference typically takes 30-60 seconds, creating
intermittent 504 Gateway Timeout errors. This spec defines a robust async job queue
system that eliminates timeout issues by immediately returning a job ID and using
client-side polling for status/results.

## Problem Statement

### Current Architecture (Synchronous)

```
Frontend                    Backend                     ML Inference
   |                           |                            |
   |--POST /api/segment------->|                            |
   |                           |--run_pipeline_on_case()--->|
   |                           |                            |
   |      (30-60s wait)        |       (processing)         |
   |                           |                            |
   |                           |<---result------------------|
   |<--200 OK + JSON-----------|                            |
```

**Problem**: HF Spaces proxy times out at ~60s, killing the connection before
the ML inference completes. The response is lost even though processing succeeds.

### Target Architecture (Async with Polling)

```
Frontend                    Backend                     ML Inference
   |                           |                            |
   |--POST /api/segment------->|                            |
   |<--202 Accepted + job_id---|                            |
   |                           |--BackgroundTask----------->|
   |                           |                            |
   |--GET /api/jobs/{id}------>|       (processing)         |
   |<--200 {status: running}---|                            |
   |                           |                            |
   |--GET /api/jobs/{id}------>|                            |
   |<--200 {status: running}---|                            |
   |                           |<---result------------------|
   |--GET /api/jobs/{id}------>|                            |
   |<--200 {status: completed, |                            |
   |        result: {...}}-----|                            |
```

**Solution**: Initial request returns in <1s. Polling requests are fast (<100ms).
No single request exceeds the proxy timeout.

## Technical Design

### 1. Backend Job Store

In-memory dictionary storing job state. This is appropriate because:
- HF Spaces runs a single uvicorn worker (no multi-worker sync needed)
- Jobs are ephemeral (results cached, cleanup after 1 hour)
- No external dependencies (Redis, DB) required

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

class JobStatus(str, Enum):
    PENDING = "pending"      # Job created, not started
    RUNNING = "running"      # Inference in progress
    COMPLETED = "completed"  # Success, results available
    FAILED = "failed"        # Error occurred

@dataclass
class Job:
    id: str
    status: JobStatus
    case_id: str
    fast_mode: bool
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: int = 0  # 0-100 percentage
    progress_message: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None

# Thread-safe job store (single writer pattern)
jobs: dict[str, Job] = {}
```

### 2. API Endpoints

#### POST /api/segment (Modified)
Returns immediately with job ID.

**Request**: Same as before
```json
{
  "case_id": "sub-strokecase0001",
  "fast_mode": true
}
```

**Response**: 202 Accepted
```json
{
  "jobId": "a1b2c3d4",
  "status": "pending",
  "message": "Segmentation job queued"
}
```

#### GET /api/jobs/{job_id}
Poll for job status and results.

**Response (Running)**:
```json
{
  "jobId": "a1b2c3d4",
  "status": "running",
  "progress": 45,
  "progressMessage": "Running DeepISLES inference...",
  "elapsedSeconds": 23.5
}
```

**Response (Completed)**:
```json
{
  "jobId": "a1b2c3d4",
  "status": "completed",
  "progress": 100,
  "progressMessage": "Segmentation complete",
  "elapsedSeconds": 42.3,
  "result": {
    "caseId": "sub-strokecase0001",
    "diceScore": 0.847,
    "volumeMl": 12.34,
    "dwiUrl": "https://...hf.space/files/a1b2c3d4/...",
    "predictionUrl": "https://...hf.space/files/a1b2c3d4/..."
  }
}
```

**Response (Failed)**:
```json
{
  "jobId": "a1b2c3d4",
  "status": "failed",
  "progress": 0,
  "progressMessage": "Error occurred",
  "elapsedSeconds": 5.2,
  "error": "Case not found: sub-invalid"
}
```

**Response (Not Found)**: 404
```json
{
  "detail": "Job not found: xyz123"
}
```

### 3. Background Task Execution

```python
from fastapi import BackgroundTasks

@router.post("/segment", response_model=SegmentJobResponse, status_code=202)
def create_segment_job(
    request: Request,
    body: SegmentRequest,
    background_tasks: BackgroundTasks
) -> SegmentJobResponse:
    """Create a segmentation job and return immediately."""
    job_id = str(uuid.uuid4())[:8]

    # Create job record
    job = Job(
        id=job_id,
        status=JobStatus.PENDING,
        case_id=body.case_id,
        fast_mode=body.fast_mode,
        created_at=datetime.now(),
    )
    jobs[job_id] = job

    # Queue background task
    background_tasks.add_task(
        run_segmentation_job,
        job_id=job_id,
        case_id=body.case_id,
        fast_mode=body.fast_mode,
        backend_url=get_backend_base_url(request),
    )

    return SegmentJobResponse(
        jobId=job_id,
        status=JobStatus.PENDING,
        message="Segmentation job queued",
    )
```

### 4. Job Execution with Progress Updates

```python
def run_segmentation_job(
    job_id: str,
    case_id: str,
    fast_mode: bool,
    backend_url: str,
) -> None:
    """Execute segmentation in background thread."""
    job = jobs.get(job_id)
    if not job:
        return

    try:
        # Mark as running
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        job.progress = 10
        job.progress_message = "Loading case data..."

        # Run inference with progress callbacks
        output_dir = RESULTS_BASE / job_id

        job.progress = 20
        job.progress_message = "Staging files for DeepISLES..."

        result = run_pipeline_on_case(
            case_id,
            output_dir=output_dir,
            fast=fast_mode,
            compute_dice=True,
            cleanup_staging=True,
            # Future: pass progress_callback for finer updates
        )

        job.progress = 90
        job.progress_message = "Computing metrics..."

        # Compute volume
        volume_ml = None
        with contextlib.suppress(Exception):
            volume_ml = round(compute_volume_ml(result.prediction_mask, threshold=0.5), 2)

        # Build result
        job.progress = 100
        job.progress_message = "Segmentation complete"
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now()
        job.result = {
            "caseId": result.case_id,
            "diceScore": result.dice_score,
            "volumeMl": volume_ml,
            "elapsedSeconds": round(result.elapsed_seconds, 2),
            "dwiUrl": f"{backend_url}/files/{job_id}/{result.case_id}/{result.input_files['dwi'].name}",
            "predictionUrl": f"{backend_url}/files/{job_id}/{result.case_id}/{result.prediction_mask.name}",
        }

    except Exception as e:
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now()
        job.error = str(e)
        job.progress_message = "Error occurred"
```

### 5. Job Cleanup (Memory Management)

```python
import threading
from datetime import timedelta

JOB_TTL = timedelta(hours=1)  # Keep completed jobs for 1 hour

def cleanup_old_jobs() -> None:
    """Remove jobs older than TTL to prevent memory leaks."""
    now = datetime.now()
    expired = [
        job_id for job_id, job in jobs.items()
        if job.completed_at and (now - job.completed_at) > JOB_TTL
    ]
    for job_id in expired:
        # Also cleanup result files
        result_dir = RESULTS_BASE / job_id
        if result_dir.exists():
            shutil.rmtree(result_dir, ignore_errors=True)
        del jobs[job_id]

# Run cleanup every 10 minutes
def start_cleanup_scheduler():
    def run():
        while True:
            time.sleep(600)  # 10 minutes
            cleanup_old_jobs()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
```

### 6. Frontend Polling Hook

```typescript
// hooks/useJobPolling.ts
import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient, JobStatus, JobStatusResponse } from '../api/client'

interface UseJobPollingOptions {
  pollingInterval?: number  // ms, default 2000
  onComplete?: (result: SegmentationResult) => void
  onError?: (error: string) => void
}

export function useJobPolling(options: UseJobPollingOptions = {}) {
  const { pollingInterval = 2000, onComplete, onError } = options

  const [jobId, setJobId] = useState<string | null>(null)
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const intervalRef = useRef<number | null>(null)
  const onCompleteRef = useRef(onComplete)
  const onErrorRef = useRef(onError)

  // Keep callbacks current
  useEffect(() => {
    onCompleteRef.current = onComplete
    onErrorRef.current = onError
  })

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setIsPolling(false)
  }, [])

  const pollJobStatus = useCallback(async (id: string) => {
    try {
      const response = await apiClient.getJobStatus(id)

      setStatus(response.status)
      setProgress(response.progress)
      setProgressMessage(response.progressMessage)

      if (response.status === 'completed' && response.result) {
        stopPolling()
        onCompleteRef.current?.(response.result)
      } else if (response.status === 'failed') {
        stopPolling()
        setError(response.error || 'Job failed')
        onErrorRef.current?.(response.error || 'Job failed')
      }
    } catch (err) {
      // Don't stop polling on network errors - might be transient
      console.warn('Polling error:', err)
    }
  }, [stopPolling])

  const startJob = useCallback(async (caseId: string, fastMode = true) => {
    // Reset state
    setError(null)
    setProgress(0)
    setProgressMessage('Starting...')
    setStatus('pending')

    try {
      // Create job
      const response = await apiClient.createSegmentJob(caseId, fastMode)
      setJobId(response.jobId)
      setStatus(response.status)

      // Start polling
      setIsPolling(true)
      intervalRef.current = window.setInterval(
        () => pollJobStatus(response.jobId),
        pollingInterval
      )

      // Initial poll
      await pollJobStatus(response.jobId)

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start job'
      setError(message)
      onErrorRef.current?.(message)
    }
  }, [pollingInterval, pollJobStatus])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  return {
    jobId,
    status,
    progress,
    progressMessage,
    error,
    isPolling,
    startJob,
    stopPolling,
  }
}
```

### 7. Frontend API Client Extensions

```typescript
// api/client.ts additions

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface CreateJobResponse {
  jobId: string
  status: JobStatus
  message: string
}

export interface JobStatusResponse {
  jobId: string
  status: JobStatus
  progress: number
  progressMessage: string
  elapsedSeconds?: number
  result?: SegmentResponse
  error?: string
}

class ApiClient {
  // ... existing methods ...

  async createSegmentJob(
    caseId: string,
    fastMode: boolean = true,
    signal?: AbortSignal
  ): Promise<CreateJobResponse> {
    const response = await fetch(`${this.baseUrl}/api/segment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: caseId, fast_mode: fastMode }),
      signal,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(
        `Failed to create job: ${error.detail || response.statusText}`,
        response.status,
        error.detail
      )
    }

    return response.json()
  }

  async getJobStatus(jobId: string, signal?: AbortSignal): Promise<JobStatusResponse> {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}`, { signal })

    if (response.status === 404) {
      throw new ApiError('Job not found', 404)
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new ApiError(
        `Failed to get job status: ${error.detail || response.statusText}`,
        response.status,
        error.detail
      )
    }

    return response.json()
  }
}
```

### 8. UI Progress Display

```tsx
// components/ProgressIndicator.tsx
interface ProgressIndicatorProps {
  progress: number
  message: string
  status: JobStatus
}

export function ProgressIndicator({ progress, message, status }: ProgressIndicatorProps) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 space-y-3">
      <div className="flex justify-between text-sm">
        <span className="text-gray-400">{message}</span>
        <span className="text-gray-300">{progress}%</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${
            status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}
```

## Implementation Checklist

### Backend
- [ ] Create `job_store.py` with Job dataclass and jobs dict
- [ ] Create Pydantic schemas for job responses
- [ ] Modify POST /api/segment to return 202 with job ID
- [ ] Add GET /api/jobs/{job_id} endpoint
- [ ] Implement background task execution with progress updates
- [ ] Add job cleanup scheduler
- [ ] Update CORS if needed for new endpoint

### Frontend
- [ ] Add job-related types to `types/index.ts`
- [ ] Add API client methods for job creation and polling
- [ ] Create `useJobPolling` hook
- [ ] Create `ProgressIndicator` component
- [ ] Update `useSegmentation` to use job polling
- [ ] Update `App.tsx` to show progress during processing

### Testing
- [ ] Unit tests for job store
- [ ] Unit tests for job endpoints
- [ ] Unit tests for useJobPolling hook
- [ ] E2E test for full job flow
- [ ] Manual test on HF Spaces deployment

### Documentation
- [ ] Update API documentation
- [ ] Update bug tracker with resolution
- [ ] Add architecture diagram

## Migration Strategy

1. **Backend**: Add new endpoints alongside existing. Keep old `/api/segment`
   temporarily for backwards compatibility (marked deprecated).

2. **Frontend**: Update to use new job polling system. Old sync behavior removed.

3. **Testing**: Verify on HF Spaces before removing deprecated endpoint.

4. **Cleanup**: Remove deprecated sync endpoint after validation.

## Performance Considerations

| Metric | Before (Sync) | After (Async) |
|--------|--------------|---------------|
| Initial response time | 30-60s | <1s |
| Total request count | 1 | ~15-30 (polling) |
| Timeout risk | HIGH | NONE |
| User feedback | None during wait | Progress updates |
| Network efficiency | 1 large response | Many small responses |

## Alternatives Considered

### 1. SSE (Server-Sent Events)
- **Pros**: Real-time updates, single connection
- **Cons**: Connection stays open (could still timeout), HF proxy issues possible
- **Decision**: Polling is more robust for HF Spaces constraints

### 2. WebSockets
- **Pros**: Bi-directional, real-time
- **Cons**: Known 404 issues on HF Spaces, complex
- **Decision**: Not viable on HF Spaces

### 3. Redis/Celery
- **Pros**: Production-grade, multi-worker support
- **Cons**: Not available on HF Spaces Docker
- **Decision**: In-memory sufficient for single-worker

## References

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI Polling Strategy for Long-Running Tasks](https://openillumi.com/en/en-fastapi-long-task-progress-polling/)
- [Managing Background Tasks in FastAPI](https://leapcell.io/blog/managing-background-tasks-and-long-running-operations-in-fastapi)
- [Real Time Polling in React Query 2025](https://samwithcode.in/tutorial/react-js/real-time-polling-in-react-query-2025)
- [504 Gateway Timeout - HF Forums](https://discuss.huggingface.co/t/504-gateway-timeout-with-http-request/24018)
