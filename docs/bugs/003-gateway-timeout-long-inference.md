# Bug 003: Gateway Timeout Risk for Long ML Inference

**Status**: DOCUMENTED (Risk Acknowledged)
**Date Found**: 2025-12-12
**Severity**: Medium (intermittent failures for slower cases)

---

## Summary

HuggingFace Spaces has an approximately 60-second proxy/gateway timeout. The DeepISLES
ML inference typically takes 30-60 seconds in fast mode. This creates a risk of
intermittent 504 Gateway Timeout errors, especially for larger or more complex cases.

## Evidence

### HF Spaces Timeout Behavior

From HuggingFace community forums:
- "When requests take longer than a minute, users get a 504 timeout error"
- "After the POST request, the inference is run, but the API does not get the result
   since it's long timed out by then"

### Current Inference Times

Based on the codebase configuration:
- Default timeout: 1800 seconds (30 minutes) in `src/stroke_deepisles_demo/core/config.py:86`
- Typical fast mode inference: 30-60 seconds (observed in deployment)
- E2E test expects results within 30 seconds: `frontend/e2e/pages/HomePage.ts:48`

## Symptoms

When this issue occurs:
1. User clicks "Run Segmentation"
2. UI shows "Processing..." for ~60 seconds
3. Browser receives 504 Gateway Timeout
4. Error displayed: "Segmentation failed: Gateway Timeout" (or similar network error)
5. Backend may still complete the inference (results exist but response lost)

## Root Cause

HuggingFace Spaces runs containers behind a reverse proxy with a hard ~60 second timeout.
This timeout is enforced at the infrastructure level and cannot be changed by:
- Uvicorn configuration
- FastAPI settings
- Client-side timeout settings
- Gradio queue settings

## Risk Assessment

| Scenario | Inference Time | Risk Level |
|----------|---------------|------------|
| Small/simple cases | 20-30s | Low |
| Typical cases | 30-45s | Medium |
| Complex/large cases | 45-60s | High |
| Edge cases | >60s | Certain failure |

## Mitigation Options

### Option 1: Accept the Risk (Current)
- Pros: Simple, no code changes needed
- Cons: Some users will experience timeouts
- Best for: Demo/prototype where occasional failures are acceptable

### Option 2: Async/Polling Pattern
```python
# 1. POST /api/segment returns job_id immediately
# 2. Frontend polls GET /api/jobs/{job_id}/status
# 3. When complete, fetch results from GET /api/jobs/{job_id}/result
```
- Pros: No timeout issues, better UX with progress updates
- Cons: Significant refactor, more complex state management

### Option 3: WebSocket/SSE for Progress
- Pros: Real-time progress updates
- Cons: WebSockets have issues on HF Spaces (reported 404 errors), SSE may work

### Option 4: Dedicated Inference Endpoint
- Use HuggingFace Inference Endpoints instead of Spaces
- Configure custom timeout limits
- Pros: Full control over timeouts
- Cons: Additional cost, separate deployment

## Current Decision

**Accept the Risk** - This is a demo application where occasional timeouts are acceptable.
The typical inference time (30-45s) usually completes within the limit.

Users who experience timeouts can:
1. Retry the same case (results may already exist from previous attempt)
2. Try a different case
3. Wait and retry if the system is under load

## Monitoring

To track this issue in production:
1. Monitor 504 error rates in HF Spaces logs
2. Track inference durations in application logs
3. Consider adding client-side timing to report slow requests

## References

- [504 Gateway Timeout with http request - HF Forums](https://discuss.huggingface.co/t/504-gateway-timeout-with-http-request/24018)
- [504 Gateway Timeout on Hugging Face space - Gradio Issue #3114](https://github.com/gradio-app/gradio/issues/3114)
- [Deploying FastAPI on HF Spaces](https://medium.com/@na.mazaheri/deploying-a-fastapi-app-on-hugging-face-spaces-and-handling-all-its-restrictions-d494d97a78fa)
