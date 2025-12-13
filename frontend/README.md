---
title: Stroke Lesion Viewer
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: static
app_file: dist/index.html
app_build_command: npm run build
# CRITICAL: Vite 7 requires Node.js >= 20. HF Spaces defaults to Node 18.
nodejs_version: "20"
pinned: false
custom_headers:
  cross-origin-embedder-policy: require-corp
  cross-origin-opener-policy: same-origin
  cross-origin-resource-policy: cross-origin
---

# Stroke Lesion Segmentation Viewer

Interactive 3D viewer for stroke lesion segmentation results using NiiVue.

Built with React, TypeScript, Tailwind CSS, and Vite.

## Features

- **NiiVue WebGL2 Viewer**: Pan, zoom, and navigate through NIfTI volumes
- **Real-time Segmentation**: Run DeepISLES inference on ISLES24 dataset cases
- **Metrics Display**: Dice score, volume (mL), processing time

## Browser Requirements

- **WebGL2 Required**: This viewer uses NiiVue which requires WebGL2 support.
- Supported browsers: Chrome 56+, Firefox 51+, Safari 15+, Edge 79+
- Test your browser: https://get.webgl.org/webgl2/
- Mobile devices may have limited support

## Architecture

This is the **frontend Static Space** of a two-Space deployment:

```
┌─────────────────────────────────────┐
│  HuggingFace Static Space           │  ← You are here
│  stroke-viewer-frontend             │
│                                     │
│  React 19 + TypeScript + Tailwind   │
│  @niivue/niivue for 3D viewing      │
└──────────────┬──────────────────────┘
               │ HTTPS API calls
               ▼
┌─────────────────────────────────────┐
│  HuggingFace Docker Space           │
│  stroke-viewer-api                  │
│                                     │
│  FastAPI + DeepISLES + PyTorch      │
└─────────────────────────────────────┘
```

## Local Development

```bash
npm install
npm run dev          # Start dev server at http://localhost:5173
npm test             # Run unit tests
npm run test:e2e     # Run E2E tests
npm run build        # Production build
```

## Environment Variables

Set `VITE_API_URL` to point to your backend:

```bash
# Local development (default)
VITE_API_URL=http://localhost:7860 npm run dev

# Production is configured in .env.production
# Points to: https://vibecodermcswaggins-stroke-deepisles-demo.hf.space
```

## Deployment

This frontend deploys as a **HuggingFace Static Space**. The backend API runs on a separate Docker Space with GPU.

```bash
# Build for production (uses .env.production)
npm run build

# The dist/ folder is deployed to HF Static Space
```

## Fork Deployment

If you fork this repository, update these files before deploying:

1. **Frontend API URL** (`frontend/.env.production`):
   ```
   VITE_API_URL=https://{YOUR_HF_USERNAME}-stroke-deepisles-demo.hf.space
   ```

2. **Backend CORS** (`src/stroke_deepisles_demo/core/config.py`):
   Set `STROKE_DEMO_FRONTEND_ORIGINS` env var (JSON list) on the backend Space:
   ```bash
   STROKE_DEMO_FRONTEND_ORIGINS='["https://{YOUR_HF_USERNAME}-stroke-viewer-frontend.hf.space"]'
   ```

3. **Rebuild frontend**:
   ```bash
   cd frontend && npm run build
   ```
