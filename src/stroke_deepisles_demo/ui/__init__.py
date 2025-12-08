"""UI module for stroke-deepisles-demo.

Exports:
    create_app: Create the Gradio application
    get_demo: Get the global demo instance (lazy initialization)
"""

from typing import Any


def __getattr__(name: str) -> Any:
    """Lazy import to avoid circular import when running as `python -m`."""
    if name in ("create_app", "get_demo"):
        from stroke_deepisles_demo.ui.app import create_app, get_demo

        return {"create_app": create_app, "get_demo": get_demo}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_app", "get_demo"]
