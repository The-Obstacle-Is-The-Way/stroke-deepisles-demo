import os

import gradio as gr
from app import demo as app

_docs = {
    "NiiVueViewer": {
        "description": "WebGL NIfTI viewer using NiiVue.",
        "members": {
            "__init__": {
                "value": {
                    "type": "NiiVueViewerData | dict[str, typing.Any] | None",
                    "default": "None",
                    "description": None,
                },
                "label": {"type": "str | None", "default": "None", "description": None},
                "height": {"type": "int", "default": "500", "description": None},
                "show_label": {"type": "bool", "default": "True", "description": None},
                "container": {"type": "bool", "default": "True", "description": None},
                "scale": {"type": "int | None", "default": "None", "description": None},
                "min_width": {"type": "int", "default": "160", "description": None},
                "visible": {"type": "bool", "default": "True", "description": None},
                "elem_id": {"type": "str | None", "default": "None", "description": None},
                "elem_classes": {
                    "type": "list[str] | str | None",
                    "default": "None",
                    "description": None,
                },
                "render": {"type": "bool", "default": "True", "description": None},
                "key": {
                    "type": "int | str | tuple[int | str, Ellipsis] | None",
                    "default": "None",
                    "description": None,
                },
            },
            "postprocess": {
                "value": {
                    "type": "dict[str, typing.Any] | None",
                    "description": "The output data received by the component from the user's function in the backend.",
                }
            },
            "preprocess": {
                "return": {
                    "type": "dict[str, typing.Any] | None",
                    "description": "The preprocessed input data sent to the user's function in the backend.",
                },
                "value": None,
            },
        },
        "events": {},
    },
    "__meta__": {
        "additional_interfaces": {
            "NiiVueViewerData": {
                "source": "class NiiVueViewerData(GradioModel):\n    background_url: str | None = None\n    overlay_url: str | None = None"
            }
        },
        "user_fn_refs": {"NiiVueViewer": []},
    },
}

abs_path = os.path.join(os.path.dirname(__file__), "css.css")

with gr.Blocks(
    css=abs_path,
    theme=gr.themes.Default(
        font_mono=[
            gr.themes.GoogleFont("Inconsolata"),
            "monospace",
        ],
    ),
) as demo:
    gr.Markdown(
        """
# `gradio_niivueviewer`

<div style="display: flex; gap: 7px;">
<img alt="Static Badge" src="https://img.shields.io/badge/version%20-%200.0.1%20-%20orange">
</div>

A Gradio custom component for 3D medical imaging visualization using NiiVue (WebGL).
""",
        elem_classes=["md-custom"],
        header_links=True,
    )
    app.render()
    gr.Markdown(
        """
## Installation

```bash
pip install gradio_niivueviewer
```

## Usage

```python
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

```
""",
        elem_classes=["md-custom"],
        header_links=True,
    )

    gr.Markdown(
        """
## `NiiVueViewer`

### Initialization
""",
        elem_classes=["md-custom"],
        header_links=True,
    )

    gr.ParamViewer(value=_docs["NiiVueViewer"]["members"]["__init__"], linkify=["NiiVueViewerData"])

    gr.Markdown(
        """

### User function

The impact on the users predict function varies depending on whether the component is used as an input or output for an event (or both).

- When used as an Input, the component only impacts the input signature of the user function.
- When used as an output, the component only impacts the return signature of the user function.

The code snippet below is accurate in cases where the component is used as both an input and an output.

- **As input:** Is passed, the preprocessed input data sent to the user's function in the backend.
- **As output:** Should return, the output data received by the component from the user's function in the backend.

 ```python
def predict(
    value: dict[str, typing.Any] | None
) -> dict[str, typing.Any] | None:
    return value
```
""",
        elem_classes=["md-custom", "NiiVueViewer-user-fn"],
        header_links=True,
    )

    code_NiiVueViewerData = gr.Markdown(
        """
## `NiiVueViewerData`
```python
class NiiVueViewerData(GradioModel):
    background_url: str | None = None
    overlay_url: str | None = None
```""",
        elem_classes=["md-custom", "NiiVueViewerData"],
        header_links=True,
    )

    demo.load(
        None,
        js=r"""function() {
    const refs = {
            NiiVueViewerData: [], };
    const user_fn_refs = {
          NiiVueViewer: [], };
    requestAnimationFrame(() => {

        Object.entries(user_fn_refs).forEach(([key, refs]) => {
            if (refs.length > 0) {
                const el = document.querySelector(`.${key}-user-fn`);
                if (!el) return;
                refs.forEach(ref => {
                    el.innerHTML = el.innerHTML.replace(
                        new RegExp("\\b"+ref+"\\b", "g"),
                        `<a href="#h-${ref.toLowerCase()}">${ref}</a>`
                    );
                })
            }
        })

        Object.entries(refs).forEach(([key, refs]) => {
            if (refs.length > 0) {
                const el = document.querySelector(`.${key}`);
                if (!el) return;
                refs.forEach(ref => {
                    el.innerHTML = el.innerHTML.replace(
                        new RegExp("\\b"+ref+"\\b", "g"),
                        `<a href="#h-${ref.toLowerCase()}">${ref}</a>`
                    );
                })
            }
        })
    })
}

""",
    )

demo.launch()
