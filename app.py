"""Entry point for Hugging Face Spaces deployment.

This module provides the entry point for deploying the stroke-deepisles-demo
application to Hugging Face Spaces. It handles environment detection and
configures Gradio appropriately for the deployment environment.

See:
    - docs/specs/07-hf-spaces-deployment.md
    - https://huggingface.co/docs/hub/spaces-sdks-docker
"""

from pathlib import Path

import gradio as gr

# CRITICAL: Allow direct file serving for local assets (niivue.js)
# This fixes the P0 "Loading..." bug on HF Spaces (Issue #11649)
# Must be called BEFORE creating any Blocks
_ASSETS_DIR = Path(__file__).parent / "src" / "stroke_deepisles_demo" / "ui" / "assets"
gr.set_static_paths(paths=[str(_ASSETS_DIR)])

from stroke_deepisles_demo.core.config import get_settings  # noqa: E402
from stroke_deepisles_demo.core.logging import setup_logging  # noqa: E402
from stroke_deepisles_demo.ui.app import get_demo  # noqa: E402
from stroke_deepisles_demo.ui.viewer import get_niivue_loader_path  # noqa: E402

# Initialize logging
settings = get_settings()
setup_logging(settings.log_level, format_style=settings.log_format)

# Create the demo instance at module level for Gradio
demo = get_demo()

if __name__ == "__main__":
    # Launch configuration
    # - server_name: 0.0.0.0 required for HF Spaces (Docker)
    # - server_port: 7860 is HF Spaces default
    # - theme: Gradio 6 uses launch() for theme
    # - css: Hide footer for cleaner look

    # Allow access to local assets (e.g., niivue.js)
    # Assets are located in src/stroke_deepisles_demo/ui/assets
    assets_dir = Path(__file__).parent / "src" / "stroke_deepisles_demo" / "ui" / "assets"

    # Generate the NiiVue loader HTML file (creates if needed)
    niivue_loader = get_niivue_loader_path()

    demo.launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=settings.gradio_share,
        theme=gr.themes.Soft(),
        css="footer {visibility: hidden}",
        allowed_paths=[str(assets_dir)],
        head_paths=[str(niivue_loader)],  # Official Gradio approach (Issue #11649)
    )
