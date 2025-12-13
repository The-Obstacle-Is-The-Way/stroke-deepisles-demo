"""Alternative entry point for local Gradio development.

NOTE: HuggingFace Spaces Docker deployment uses FastAPI via uvicorn:
  uvicorn stroke_deepisles_demo.api.main:app --host 0.0.0.0 --port 7860
(see Dockerfile CMD). This file runs the legacy Gradio UI for local development.

For HF Spaces deployment, see: src/stroke_deepisles_demo/api/main.py
For legacy Gradio UI, see: src/stroke_deepisles_demo/ui/app.py
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
