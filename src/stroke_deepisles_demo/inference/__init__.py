"""Inference module for stroke-deepisles-demo."""

from stroke_deepisles_demo.inference.deepisles import (
    DEEPISLES_IMAGE,
    DeepISLESResult,
    run_deepisles_on_folder,
    validate_input_folder,
)
from stroke_deepisles_demo.inference.docker import (
    DockerRunResult,
    build_docker_command,
    check_docker_available,
    ensure_docker_available,
    run_container,
)

__all__ = [
    "DEEPISLES_IMAGE",
    "DeepISLESResult",
    "DockerRunResult",
    "build_docker_command",
    "check_docker_available",
    "ensure_docker_available",
    "run_container",
    "run_deepisles_on_folder",
    "validate_input_folder",
]
