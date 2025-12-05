"""Inference module for stroke-deepisles-demo."""

from stroke_deepisles_demo.inference.deepisles import (
    DEEPISLES_IMAGE,
    DeepISLESResult,
    find_prediction_mask,
    run_deepisles_on_folder,
    validate_input_folder,
)
from stroke_deepisles_demo.inference.docker import (
    DockerRunResult,
    build_docker_command,
    check_docker_available,
    check_nvidia_docker_available,
    ensure_docker_available,
    ensure_gpu_available_if_requested,
    pull_image_if_missing,
    run_container,
)

__all__ = [
    # DeepISLES
    "DEEPISLES_IMAGE",
    "DeepISLESResult",
    # Docker utilities
    "DockerRunResult",
    "build_docker_command",
    "check_docker_available",
    "check_nvidia_docker_available",
    "ensure_docker_available",
    "ensure_gpu_available_if_requested",
    "find_prediction_mask",
    "pull_image_if_missing",
    "run_container",
    "run_deepisles_on_folder",
    "validate_input_folder",
]
