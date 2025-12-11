---
title: Stroke Lesion Viewer
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: static
app_file: dist/index.html
app_build_command: npm run build
# CRITICAL: Vite 6 requires Node.js >= 20. HF Spaces defaults to Node 18.
# Without this, the build will fail or produce warnings.
nodejs_version: "20"
pinned: false
---

# Stroke Lesion Segmentation Viewer

Interactive 3D viewer for stroke lesion segmentation results using NiiVue.

Built with React, TypeScript, Tailwind CSS, and Vite.

## Features

- **NiiVue WebGL2 Viewer**: Pan, zoom, and navigate through NIfTI volumes
- **Real-time Segmentation**: Run DeepISLES inference on ISLES24 dataset cases
- **Metrics Display**: Dice score, volume (mL), processing time

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
VITE_API_URL=http://localhost:7860 npm run dev
```
