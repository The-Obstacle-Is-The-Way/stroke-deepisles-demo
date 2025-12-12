# Bug 003: Gateway Timeout Risk for Long ML Inference

**Status**: FIXED
**Date Found**: 2025-12-12
**Date Fixed**: 2025-12-12
**Severity**: Medium (was causing intermittent failures)

---

## Summary

HuggingFace Spaces has an approximately 60-second proxy/gateway timeout. The DeepISLES
ML inference typically takes 30-60 seconds in fast mode, which was causing intermittent
504 Gateway Timeout errors.

**Solution**: Implemented async job queue pattern with client-side polling.

## Original Problem

### HF Spaces Timeout Behavior

From HuggingFace community forums:
- "When requests take longer than a minute, users get a 504 timeout error"
- "After the POST request, the inference is run, but the API does not get the result
   since it's long timed out by then"

### Symptoms

When this issue occurred:
1. User clicks "Run Segmentation"
2. UI shows "Processing..." for ~60 seconds
3. Browser receives 504 Gateway Timeout
4. Error displayed: "Segmentation failed: Gateway Timeout"
5. Backend may still complete the inference (results exist but response lost)

## Solution: Async Job Queue Pattern

### Architecture

```
BEFORE (Synchronous - Timeout Risk):
  Frontend                    Backend
     |--POST /api/segment------->|
     |       (30-60s wait)       |
     |<--200 OK + results--------|  # TIMEOUT!

AFTER (Async with Polling - No Timeout):
  Frontend                    Backend
     |--POST /api/segment------->|
     |<--202 + jobId (<1s)-------|
     |--GET /api/jobs/{id}------>|
     |<--200 {progress: 30%}----|
     |--GET /api/jobs/{id}------>|
     |<--200 {progress: 70%}----|
     |--GET /api/jobs/{id}------>|
     |<--200 {complete, result}--|
```

### Implementation

#### Backend Changes

1. **Job Store** (`src/stroke_deepisles_demo/api/job_store.py`)
   - In-memory job storage with thread-safe operations
   - Automatic cleanup of old jobs (1 hour TTL)
   - Progress tracking with status updates

2. **Routes** (`src/stroke_deepisles_demo/api/routes.py`)
   - `POST /api/segment` returns 202 with job ID immediately
   - `GET /api/jobs/{job_id}` returns current status/progress/results
   - Background task executes inference

3. **Schemas** (`src/stroke_deepisles_demo/api/schemas.py`)
   - `CreateJobResponse` for job creation
   - `JobStatusResponse` for polling

#### Frontend Changes

1. **Types** (`frontend/src/types/index.ts`)
   - `JobStatus`, `CreateJobResponse`, `JobStatusResponse`

2. **API Client** (`frontend/src/api/client.ts`)
   - `createSegmentJob()` - creates job
   - `getJobStatus()` - polls for status

3. **Hook** (`frontend/src/hooks/useSegmentation.ts`)
   - Polls every 2 seconds
   - Tracks progress, status, elapsed time
   - Handles completion and errors

4. **Components**
   - `ProgressIndicator` - shows progress bar and status
   - `App` - integrates progress display and cancel button

### Spec Document

Full specification: `docs/specs/async-job-queue.md`

## Performance Impact

| Metric | Before (Sync) | After (Async) |
|--------|--------------|---------------|
| Initial response time | 30-60s | <1s |
| Total request count | 1 | ~15-30 (polling) |
| Timeout risk | HIGH | NONE |
| User feedback | None during wait | Real-time progress |

## Files Changed

### Backend
- `src/stroke_deepisles_demo/api/job_store.py` (NEW)
- `src/stroke_deepisles_demo/api/schemas.py`
- `src/stroke_deepisles_demo/api/routes.py`
- `src/stroke_deepisles_demo/api/main.py`

### Frontend
- `frontend/src/types/index.ts`
- `frontend/src/api/client.ts`
- `frontend/src/hooks/useSegmentation.ts`
- `frontend/src/components/ProgressIndicator.tsx` (NEW)
- `frontend/src/App.tsx`
- `frontend/src/mocks/handlers.ts`

### Tests
- `frontend/src/api/__tests__/client.test.ts`
- `frontend/src/hooks/__tests__/useSegmentation.test.tsx`
- `frontend/src/App.test.tsx`

## Verification

After fix:
1. Deploy backend to HF Spaces
2. Refresh frontend
3. Run segmentation on any case
4. Observe progress bar updating in real-time
5. Results display after completion - NO timeout errors

## References

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI Polling Strategy](https://openillumi.com/en/en-fastapi-long-task-progress-polling/)
- [504 Gateway Timeout - HF Forums](https://discuss.huggingface.co/t/504-gateway-timeout-with-http-request/24018)
- [Real Time Polling in React Query 2025](https://samwithcode.in/tutorial/react-js/real-time-polling-in-react-query-2025)
