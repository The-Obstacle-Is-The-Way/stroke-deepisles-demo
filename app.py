"""Entry point for Hugging Face Spaces deployment."""

import gradio as gr

from stroke_deepisles_demo.ui.app import get_demo

# Create the demo instance at module level for Gradio
demo = get_demo()

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), css="footer {visibility: hidden}")
