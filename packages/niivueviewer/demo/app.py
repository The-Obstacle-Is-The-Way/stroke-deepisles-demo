import gradio as gr
from gradio_niivueviewer import NiiVueViewer

example = NiiVueViewer().example_value()

demo = gr.Interface(
    lambda x: x,
    NiiVueViewer(),  # interactive version of your component
    NiiVueViewer(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()
