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

    # CRITICAL FIX (Issue #24): Load NiiVue via head= parameter
    #
    # The head= parameter injects a <script type="module"> into <head> that loads
    # NiiVue BEFORE Gradio's Svelte app hydrates. This is critical because:
    #
    # 1. Dynamic import() inside js_on_load blocks Svelte hydration on HF Spaces
    # 2. head= scripts run BEFORE Gradio mounts, so failures don't block the app
    # 3. js_on_load then just USES window.Niivue (no imports)
    #
    # Evidence: A/B test in docs/specs/24-bug-hf-spaces-loading-forever.md showed
    # disabling js_on_load makes the app load. The fix is head= for loading.

    demo.launch(
        server_name=settings.gradio_server_name,
        server_port=settings.gradio_server_port,
        share=settings.gradio_share,
        theme=gr.themes.Soft(),
        css="footer {visibility: hidden}",
        head=get_niivue_head_html(),  # Load NiiVue before Gradio hydrates
        allowed_paths=[str(_ASSETS_DIR)],
    )
