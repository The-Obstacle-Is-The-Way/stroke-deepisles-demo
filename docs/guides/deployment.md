# Deployment

The demo consists of two components deployed to Hugging Face Spaces:
1. **Backend (FastAPI)**: Docker SDK Space running DeepISLES inference
2. **Frontend (React SPA)**: Static SDK Space hosting the viewer UI

## Architecture

```
┌──────────────────────────┐     ┌──────────────────────────┐
│  Frontend HF Space       │     │  Backend HF Space        │
│  (Static SDK)            │────▶│  (Docker SDK + GPU)      │
│  React + NiiVue          │     │  FastAPI + DeepISLES     │
└──────────────────────────┘     └──────────────────────────┘
```

## Backend: HuggingFace Spaces (Docker SDK)

### Prerequisites
- HuggingFace account
- Space with GPU allocation (T4-small minimum for inference)

### Steps

1. **Create a Docker SDK Space**:
   - Go to [huggingface.co/spaces](https://huggingface.co/spaces)
   - SDK: **Docker** (required for custom dependencies)
   - Hardware: **T4-small** or better (DeepISLES requires GPU)

2. **Push your code**:
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_ORG/YOUR_SPACE
   git push hf main
   ```

3. **Configure Secrets** (Settings → Secrets):
   - `HF_TOKEN`: Read-only token for gated datasets (optional)
   - `STROKE_DEMO_FRONTEND_ORIGINS`: JSON array of allowed frontend origins

### How It Works

The Dockerfile:
- Uses `isleschallenge/deepisles` as base (includes nnU-Net, SEALS, weights)
- Installs demo package in `/home/user/demo` (avoids overwriting DeepISLES at `/app`)
- Runs FastAPI on port 7860 (HF Spaces default)
- Uses **direct invocation** (subprocess to conda env) instead of Docker-in-Docker

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_SPACES` | `1` | Auto-set by HF; triggers direct invocation mode |
| `DEEPISLES_DIRECT_INVOCATION` | `1` | Forces subprocess mode (no Docker-in-Docker) |
| `STROKE_DEMO_FRONTEND_ORIGINS` | `[]` | JSON array of CORS-allowed origins |
| `HF_TOKEN` | (none) | For gated datasets |

## Frontend: HuggingFace Spaces (Static SDK)

### Steps

1. **Create a Static SDK Space**:
   - SDK: **Static**
   - No hardware needed (static files only)

2. **Build and deploy**:
   ```bash
   cd frontend
   npm install
   VITE_API_URL=https://your-backend.hf.space npm run build
   # Copy dist/* to your Static Space
   ```

3. **Configure API URL**:
   Set `VITE_API_URL` at build time to point to your backend Space.

## Local Development

### Backend Only
```bash
docker pull isleschallenge/deepisles
uv sync
uv run uvicorn stroke_deepisles_demo.api.main:app --reload --port 7860
```

### Frontend Only
```bash
cd frontend
npm install
VITE_API_URL=http://localhost:7860 npm run dev
```

### Full Stack
```bash
# Terminal 1: Backend
uv run uvicorn stroke_deepisles_demo.api.main:app --reload --port 7860

# Terminal 2: Frontend
cd frontend && npm run dev
```

## Legacy: Gradio UI

The project includes a legacy Gradio interface at `app.py`:
```bash
uv run python -m stroke_deepisles_demo.ui.app
```

This is provided for backwards compatibility but is not the primary deployment target.
The Gradio UI connects directly to DeepISLES without the job queue.

## Troubleshooting

### "GPU not available" warning
- Ensure your Space has GPU hardware allocated (T4-small minimum)
- Check Space settings → Hardware

### CORS errors in browser
- Set `STROKE_DEMO_FRONTEND_ORIGINS` to include your frontend URL
- Format: `'["https://your-frontend.hf.space"]'`

### Inference timeouts
- Default timeout is 30 minutes (`STROKE_DEMO_DEEPISLES_TIMEOUT_SECONDS`)
- T4-small handles most cases; larger volumes may need more GPU memory
