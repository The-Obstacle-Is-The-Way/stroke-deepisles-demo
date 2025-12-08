---
title: Stroke DeepISLES Demo
emoji: "\U0001F9E0"
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
suggested_hardware: t4-small
pinned: false
license: mit
short_description: Ischemic stroke lesion segmentation using DeepISLES
models:
  - isleschallenge/deepisles
datasets:
  - hugging-science/isles24-stroke
tags:
  - medical-imaging
  - stroke
  - segmentation
  - neuroimaging
  - niivue
  - nnunet
---

# Stroke DeepISLES Demo

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

A demonstration pipeline and UI for ischemic stroke lesion segmentation using **DeepISLES** and **ISLES'24** data.

This project provides a complete end-to-end workflow:
1.  **Data Loading**: Lazy-loading of NIfTI neuroimaging data from HuggingFace.
2.  **Inference**: Running DeepISLES segmentation (SEALS or Ensemble) via Docker.
3.  **Visualization**: Interactive 3D and multi-planar viewing with NiiVue in Gradio.

> **Disclaimer**: This software is for research and demonstration purposes only. It is not intended for clinical use.

## Features

-   🧠 **State-of-the-Art Segmentation**: Uses DeepISLES (ISLES'22 winner) for accurate lesion segmentation.
-   ☁️ **Cloud-Native Data**: Streams data directly from HuggingFace Datasets (no massive downloads).
-   🐳 **Dockerized Inference**: Encapsulates complex deep learning dependencies in a reproducible container.
-   🖥️ **Interactive UI**: Gradio-based web interface with 3D rendering (NiiVue).
-   ⚙️ **Production Ready**: Type-safe, tested, and configurable via environment variables.

## Quickstart

### Prerequisites

-   Python 3.11+
-   Docker (for inference)
-   [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/The-Obstacle-Is-The-Way/stroke-deepisles-demo.git
cd stroke-deepisles-demo

# Install dependencies
uv sync
```

### Running the Demo

1.  **Pull the Docker image** (first time only):
    ```bash
    docker pull isleschallenge/deepisles
    ```

2.  **Launch the UI**:
    ```bash
    uv run python -m stroke_deepisles_demo.ui.app
    ```
    Open [http://localhost:7860](http://localhost:7860) in your browser.

3.  **Run via CLI**:
    ```bash
    # List cases
    uv run stroke-demo list

    # Run segmentation on a specific case
    uv run stroke-demo run --case sub-stroke0001
    ```

## Documentation

-   [Quickstart Guide](docs/guides/quickstart.md)
-   [Configuration](docs/guides/configuration.md)
-   [Deployment](docs/guides/deployment.md)
-   [Contributing](CONTRIBUTING.md)

## Architecture

```mermaid
graph TD
    HF[HuggingFace Hub] -->|Stream NIfTI| Loader[Data Loader]
    Loader -->|Stage Files| Staging[Staging Dir]
    Staging -->|Mount Volume| Docker[DeepISLES Container]
    Docker -->|Inference| Results[Prediction Mask]
    Results -->|Load| Metrics[Metrics (Dice)]
    Results -->|Render| UI[Gradio UI / NiiVue]
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgements

-   [DeepISLES](https://github.com/ezequieldlrosa/DeepIsles) team for the segmentation model.
-   [ISLES24](https://www.isles-challenge.org/) challenge for the dataset.
-   [NiiVue](https://github.com/niivue/niivue) for the web-based neuroimaging viewer.
