from __future__ import annotations

from typing import Any

from gradio.components.base import Component
from gradio.data_classes import GradioModel


class NiiVueViewerData(GradioModel):
    background_url: str | None = None
    overlay_url: str | None = None


class NiiVueViewer(Component):
    """WebGL NIfTI viewer using NiiVue."""

    data_model = NiiVueViewerData

    def __init__(
        self,
        value: NiiVueViewerData | dict[str, Any] | None = None,
        *,
        label: str | None = None,
        height: int = 500,
        show_label: bool = True,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        visible: bool = True,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        render: bool = True,
        key: int | str | tuple[int | str, ...] | None = None,
    ):
        self.height = height
        super().__init__(
            label=label,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            render=render,
            key=key,
            value=value,
        )

    def preprocess(self, payload: NiiVueViewerData | None) -> dict[str, Any] | None:
        if payload is None:
            return None
        return {
            "background_url": payload.background_url,
            "overlay_url": payload.overlay_url,
        }

    def postprocess(self, value: dict[str, Any] | None) -> NiiVueViewerData | None:
        if value is None:
            return None
        # Handle dict input (typical usage in app)
        return NiiVueViewerData(
            background_url=value.get("background_url"),
            overlay_url=value.get("overlay_url"),
        )

    def example_payload(self) -> Any:
        return {
            "background_url": "https://niivue.github.io/niivue/images/mni152.nii.gz",
            "overlay_url": None,
        }

    def example_value(self) -> Any:
        return {
            "background_url": "https://niivue.github.io/niivue/images/mni152.nii.gz",
            "overlay_url": None,
        }
