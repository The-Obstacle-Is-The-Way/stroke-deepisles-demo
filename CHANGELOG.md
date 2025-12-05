# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
-   **Phase 5**: Polish, Observability, and Documentation
    -   Structured logging via `stroke_deepisles_demo.core.logging`.
    -   Enhanced configuration via `pydantic-settings`.
    -   Comprehensive documentation (README, CONTRIBUTING, guides).
    -   GitHub Actions CI pipeline.

-   **Phase 4**: Gradio UI and Visualization
    -   Interactive Gradio application (`ui/app.py`).
    -   NiiVue integration for 3D/multi-planar visualization.
    -   Matplotlib slice comparison plots.

-   **Phase 3**: End-to-End Pipeline
    -   `PipelineResult` and `run_pipeline_on_case`.
    -   Metrics calculation (Dice score, Volume).
    -   CLI (`stroke-demo`) with `list` and `run` commands.

-   **Phase 2**: DeepISLES Docker Integration
    -   Wrapper for DeepISLES Docker container.
    -   Automatic GPU detection and fallback.
    -   Input/Output validation and staging.

-   **Phase 1**: Data Access Layer
    -   Integration with HuggingFace Datasets (ISLES24-MR-Lite).
    -   Local NIfTI file adapter.
    -   Lazy loading of large neuroimaging files.

-   **Phase 0**: Repository Bootstrap
    -   Project structure with `uv` and `hatchling`.
    -   Strict typing with `mypy`.
    -   Linting/Formatting with `ruff`.
    -   Testing with `pytest`.
