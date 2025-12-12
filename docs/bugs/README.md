# Bug Tracker: HuggingFace Spaces Deployment

This directory tracks bugs found during deployment to HuggingFace Spaces.

## Active Bugs

None currently.

## Fixed Bugs

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| [001](./001-cors-static-files-hf-spaces.md) | CORS regex blocking static file requests | Critical | FIXED |
| [002](./002-http-vs-https-proxy-headers.md) | HTTP vs HTTPS URL mismatch behind proxy | High | FIXED |

## Common HuggingFace Spaces Pitfalls

Based on research and experience, here are common issues to watch for:

### 1. CORS Configuration
- HF Spaces URLs use single hyphens: `{username}-{spacename}.hf.space`
- Proxy/embed URLs may use double hyphens: `{username}--{spacename}--{hash}.hf.space`
- Always use a permissive regex that matches both formats

### 2. HTTPS Behind Proxy
- HF Spaces terminates SSL at their proxy
- Uvicorn sees HTTP internally
- Add `--proxy-headers` to trust `X-Forwarded-Proto`
- Or explicitly set `BACKEND_PUBLIC_URL` environment variable

### 3. File System Restrictions
- Only `/tmp` is writable
- Use `/tmp/stroke-results` for output files
- Ensure directories are created with proper permissions

### 4. Static Files
- Mount static files AFTER directory exists
- Ensure CORS allows file fetches from frontend origin
- Files served from `/files/...` must be accessible

### 5. Environment Variables
- `HF_SPACES=1` indicates running on HF Spaces
- `SPACE_ID` contains the space identifier
- Use these to detect production environment

## Sources

- [Deploying FastAPI on HuggingFace Spaces](https://huggingface.co/blog/HemanthSai7/deploy-applications-on-huggingface-spaces)
- [HF Spaces Restrictions](https://medium.com/@na.mazaheri/deploying-a-fastapi-app-on-hugging-face-spaces-and-handling-all-its-restrictions-d494d97a78fa)
- [FastAPI HTTPS Discussion](https://github.com/fastapi/fastapi/discussions/6670)
- [HF Docker Spaces Docs](https://huggingface.co/docs/hub/en/spaces-sdks-docker)
