"""Alternative entry point for local development.

NOTE: HuggingFace Spaces Docker deployment uses `python -m stroke_deepisles_demo.ui.app`
(see Dockerfile CMD). This file is for local development convenience only.

For HF Spaces deployment, see: src/stroke_deepisles_demo/ui/app.py
"""

from pathlib import Path

import gradio as gr

# CRITICAL: Allow direct file serving for local assets (niivue.js)
# Must be called BEFORE creating any Blocks
_ASSETS_DIR = Path(__file__).parent / "src" / "stroke_deepisles_demo" / "ui" / "assets"
gr.set_static_paths(paths=[str(_ASSETS_DIR)])

from stroke_deepisles_demo.core.config import get_settings  # noqa: E402
from stroke_deepisles_demo.core.logging import get_logger, setup_logging  # noqa: E402
from stroke_deepisles_demo.ui.app import get_demo  # noqa: E402
from stroke_deepisles_demo.ui.viewer import get_niivue_head_html  # noqa: E402

logger = get_logger(__name__)

# Initialize logging
settings = get_settings()
setup_logging(settings.log_level, format_style=settings.log_format)

# Create the demo instance at module level for Gradio
demo = get_demo()

if __name__ == "__main__":
    # Log startup info for debugging
    logger.info("=" * 60)
    logger.info("STARTUP: stroke-deepisles-demo (root app.py)")
    logger.info("Assets directory: %s", _ASSETS_DIR.resolve())
    logger.info("Assets exists: %s", _ASSETS_DIR.exists())
    logger.info("=" * 60)

    # Get the NiiVue loader HTML (inline script, no file I/O needed)
    niivue_head = get_niivue_head_html()

    demo.launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=settings.gradio_share,
        theme=gr.themes.Soft(),
        css="footer {visibility: hidden}",
        allowed_paths=[str(_ASSETS_DIR)],
        head=niivue_head,  # Inject NiiVue loader directly
    )
