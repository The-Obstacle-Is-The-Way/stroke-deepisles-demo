"""Alternative entry point for local development.

NOTE: HuggingFace Spaces Docker deployment uses `python -m stroke_deepisles_demo.ui.app`
(see Dockerfile CMD). This file is for local development convenience only.

For HF Spaces deployment, see: src/stroke_deepisles_demo/ui/app.py
"""

import gradio as gr

from stroke_deepisles_demo.core.config import get_settings
from stroke_deepisles_demo.core.logging import get_logger, setup_logging
from stroke_deepisles_demo.ui.app import get_demo

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
    logger.info("=" * 60)

    demo.launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=settings.gradio_share,
        theme=gr.themes.Soft(),
        css="footer {visibility: hidden}",
    )
