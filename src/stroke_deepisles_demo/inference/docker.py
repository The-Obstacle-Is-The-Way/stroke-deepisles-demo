"""Docker execution utilities."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from stroke_deepisles_demo.core.exceptions import (
    DockerGPUNotAvailableError,
    DockerNotAvailableError,
)
from stroke_deepisles_demo.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

logger = get_logger(__name__)


@dataclass(frozen=True)
class DockerRunResult:
    """Result of a Docker container run."""

    exit_code: int
    stdout: str
    stderr: str
    elapsed_seconds: float


def check_docker_available() -> bool:
    """
    Check if Docker is installed and the daemon is running.

    Returns:
        True if Docker is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def ensure_docker_available() -> None:
    """
    Ensure Docker is available, raising if not.

    Raises:
        DockerNotAvailableError: If Docker is not installed or not running
    """
    if not check_docker_available():
        raise DockerNotAvailableError(
            "Docker is not available. Please ensure Docker is installed and running."
        )


def check_nvidia_docker_available() -> bool:
    """
    Check if NVIDIA Container Runtime is available for GPU support.

    Returns:
        True if nvidia-docker/nvidia-container-toolkit is configured
    """
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--gpus",
                "all",
                "nvidia/cuda:11.0-base",
                "nvidia-smi",
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def ensure_gpu_available_if_requested(gpu: bool) -> None:
    """
    Verify GPU is available if requested.

    Args:
        gpu: Whether GPU was requested

    Raises:
        DockerGPUNotAvailableError: If GPU requested but not available
    """
    if gpu and not check_nvidia_docker_available():
        raise DockerGPUNotAvailableError(
            "GPU requested but NVIDIA Container Runtime not available. "
            "Either install nvidia-container-toolkit or set gpu=False."
        )


def pull_image_if_missing(image: str, *, timeout: float = 600) -> bool:
    """
    Pull a Docker image if not present locally.

    Args:
        image: Docker image name (e.g., "isleschallenge/deepisles")
        timeout: Maximum seconds to wait for pull

    Returns:
        True if image was pulled, False if already present
    """
    # Check if image exists locally
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode == 0:
        logger.debug("Docker image %s already present", image)
        return False  # Image already present

    # Pull the image
    logger.info("Pulling Docker image %s (this may take a while)", image)
    subprocess.run(
        ["docker", "pull", image],
        capture_output=True,
        timeout=timeout,
        check=True,
    )
    logger.info("Successfully pulled Docker image %s", image)
    return True


def build_docker_command(
    image: str,
    *,
    command: Sequence[str] | None = None,
    volumes: dict[Path, str] | None = None,
    environment: dict[str, str] | None = None,
    gpu: bool = False,
    remove: bool = True,
    match_user: bool = True,
) -> list[str]:
    """
    Build the docker run command without executing.

    Args:
        image: Docker image name
        command: Command to run in container
        volumes: Volume mounts (host path -> container path)
        environment: Environment variables
        gpu: If True, pass --gpus all
        remove: If True, remove container after exit (--rm)
        match_user: If True, match host user (Linux only)

    Returns:
        List of command arguments for subprocess
    """
    cmd: list[str] = ["docker", "run"]

    if remove:
        cmd.append("--rm")

    if gpu:
        cmd.extend(["--gpus", "all"])

    # Match host user to avoid permission issues (Linux only).
    # Guard against platforms (e.g. Windows, macOS) where os.getuid()/getgid()
    # are absent or not meaningful.
    if match_user:
        import os

        if (
            os.name == "posix"
            and sys.platform != "darwin"
            and hasattr(os, "getuid")
            and hasattr(os, "getgid")
        ):
            uid = os.getuid()
            gid = os.getgid()
            cmd.extend(["--user", f"{uid}:{gid}"])

    if volumes:
        for host_path, container_path in volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])

    if environment:
        for key, value in environment.items():
            cmd.extend(["-e", f"{key}={value}"])

    cmd.append(image)

    if command:
        cmd.extend(command)

    return cmd


def run_container(
    image: str,
    *,
    command: Sequence[str] | None = None,
    volumes: dict[Path, str] | None = None,
    environment: dict[str, str] | None = None,
    gpu: bool = False,
    remove: bool = True,
    timeout: float | None = None,
) -> DockerRunResult:
    """
    Run a Docker container and wait for completion.

    Args:
        image: Docker image name
        command: Command to run in container
        volumes: Volume mounts (host path -> container path)
        environment: Environment variables
        gpu: If True, pass --gpus all
        remove: If True, remove container after exit (--rm)
        timeout: Maximum seconds to wait (None = no timeout)

    Returns:
        DockerRunResult with exit code, stdout, stderr, elapsed time

    Raises:
        DockerNotAvailableError: If Docker is not available
        subprocess.TimeoutExpired: If timeout exceeded
    """
    ensure_docker_available()

    cmd = build_docker_command(
        image,
        command=command,
        volumes=volumes,
        environment=environment,
        gpu=gpu,
        remove=remove,
    )

    start_time = time.time()
    # Redact environment variable values to avoid leaking secrets in logs
    redacted_cmd: list[str] = []
    skip_next = False
    for arg in cmd:
        if skip_next:
            redacted_cmd.append("***")
            skip_next = False
        elif arg == "-e":
            redacted_cmd.append(arg)
            skip_next = True
        else:
            redacted_cmd.append(arg)
    logger.debug("Running container: %s", " ".join(redacted_cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    elapsed = time.time() - start_time

    if result.returncode != 0:
        logger.error(
            "Container execution failed (code %d). stderr: %s", result.returncode, result.stderr
        )
    else:
        logger.info("Container execution completed in %.2fs", elapsed)

    return DockerRunResult(
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        elapsed_seconds=elapsed,
    )
