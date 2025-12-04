# phase 2: deepisles docker integration

## purpose

Create a Python wrapper that calls the DeepISLES Docker image as a black box. At the end of this phase, we can run stroke lesion segmentation on a folder of NIfTI files and get back the predicted mask.

## deliverables

- [ ] `src/stroke_deepisles_demo/inference/docker.py` - Docker execution wrapper
- [ ] `src/stroke_deepisles_demo/inference/deepisles.py` - DeepISLES-specific CLI interface
- [ ] Unit tests with subprocess mocking
- [ ] Integration test (marked, requires Docker)

## vertical slice outcome

After this phase, you can run:

```python
from stroke_deepisles_demo.inference import run_deepisles_on_folder

# input_dir contains: dwi.nii.gz, adc.nii.gz
result = run_deepisles_on_folder(
    input_dir=Path("/path/to/staged/case"),
    fast=True,
)
print(f"Prediction mask: {result.prediction_path}")
print(f"Elapsed: {result.elapsed_seconds:.1f}s")
```

## module structure

```
src/stroke_deepisles_demo/inference/
├── __init__.py          # Public API exports
├── docker.py            # Generic Docker execution utilities
└── deepisles.py         # DeepISLES-specific wrapper
```

## deepisles cli reference

From the [DeepIsles repository](https://github.com/ezequieldlrosa/DeepIsles), the Docker interface expects:

```bash
docker run --rm \
    -v /path/to/input:/input \
    -v /path/to/output:/output \
    --gpus all \
    isleschallenge/deepisles \
    --dwi_file_name dwi.nii.gz \
    --adc_file_name adc.nii.gz \
    [--flair_file_name flair.nii.gz] \
    --fast True  # Single model mode, faster
```

**Expected input files:**
- `dwi.nii.gz` (required) - Diffusion-weighted imaging
- `adc.nii.gz` (required) - Apparent diffusion coefficient
- `flair.nii.gz` (optional) - FLAIR sequence

**Output:**
- `results/` directory containing the lesion mask

## interfaces and types

### `inference/docker.py`

```python
"""Docker execution utilities."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from stroke_deepisles_demo.core.exceptions import DockerNotAvailableError


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
    ...


def ensure_docker_available() -> None:
    """
    Ensure Docker is available, raising if not.

    Raises:
        DockerNotAvailableError: If Docker is not installed or not running
    """
    ...


def pull_image_if_missing(image: str, *, timeout: float = 600) -> bool:
    """
    Pull a Docker image if not present locally.

    Args:
        image: Docker image name (e.g., "isleschallenge/deepisles")
        timeout: Maximum seconds to wait for pull

    Returns:
        True if image was pulled, False if already present
    """
    ...


def run_container(
    image: str,
    *,
    command: Sequence[str] | None = None,
    volumes: dict[Path, str] | None = None,  # host_path -> container_path
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
    ...


def build_docker_command(
    image: str,
    *,
    command: Sequence[str] | None = None,
    volumes: dict[Path, str] | None = None,
    environment: dict[str, str] | None = None,
    gpu: bool = False,
    remove: bool = True,
) -> list[str]:
    """
    Build the docker run command without executing.

    Useful for logging/debugging.

    Returns:
        List of command arguments for subprocess
    """
    ...
```

### `inference/deepisles.py`

```python
"""DeepISLES stroke segmentation wrapper."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from stroke_deepisles_demo.core.config import settings
from stroke_deepisles_demo.core.exceptions import DeepISLESError, MissingInputError
from stroke_deepisles_demo.inference.docker import (
    DockerRunResult,
    ensure_docker_available,
    run_container,
)


@dataclass(frozen=True)
class DeepISLESResult:
    """Result of DeepISLES inference."""

    prediction_path: Path
    docker_result: DockerRunResult
    elapsed_seconds: float


def validate_input_folder(input_dir: Path) -> tuple[Path, Path, Path | None]:
    """
    Validate that input folder contains required files.

    Args:
        input_dir: Directory to validate

    Returns:
        Tuple of (dwi_path, adc_path, flair_path_or_none)

    Raises:
        MissingInputError: If required files are missing
    """
    ...


def run_deepisles_on_folder(
    input_dir: Path,
    *,
    output_dir: Path | None = None,
    fast: bool = True,
    gpu: bool = True,
    timeout: float | None = 1800,  # 30 minutes default
) -> DeepISLESResult:
    """
    Run DeepISLES stroke segmentation on a folder of NIfTI files.

    Args:
        input_dir: Directory containing dwi.nii.gz, adc.nii.gz, [flair.nii.gz]
        output_dir: Where to write results (default: input_dir/results)
        fast: If True, use single-model mode (faster, slightly less accurate)
        gpu: If True, use GPU acceleration
        timeout: Maximum seconds to wait for inference

    Returns:
        DeepISLESResult with path to prediction mask

    Raises:
        DockerNotAvailableError: If Docker is not available
        MissingInputError: If required input files are missing
        DeepISLESError: If inference fails (non-zero exit, missing output)

    Example:
        >>> result = run_deepisles_on_folder(Path("/data/case001"), fast=True)
        >>> print(result.prediction_path)
        /data/case001/results/prediction.nii.gz
    """
    ...


def find_prediction_mask(output_dir: Path) -> Path:
    """
    Find the prediction mask in DeepISLES output directory.

    DeepISLES outputs may have varying names depending on version.
    This function finds the most likely prediction file.

    Args:
        output_dir: DeepISLES output directory

    Returns:
        Path to the prediction mask NIfTI file

    Raises:
        DeepISLESError: If no prediction mask found
    """
    ...


# Constants
DEEPISLES_IMAGE = "isleschallenge/deepisles"
EXPECTED_INPUT_FILES = ["dwi.nii.gz", "adc.nii.gz"]
OPTIONAL_INPUT_FILES = ["flair.nii.gz"]
```

### `inference/__init__.py` (public API)

```python
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
    # DeepISLES
    "run_deepisles_on_folder",
    "validate_input_folder",
    "DeepISLESResult",
    "DEEPISLES_IMAGE",
    # Docker utilities
    "check_docker_available",
    "ensure_docker_available",
    "run_container",
    "build_docker_command",
    "DockerRunResult",
]
```

## tdd plan

### test file structure

```
tests/
├── inference/
│   ├── __init__.py
│   ├── test_docker.py       # Tests for Docker utilities
│   └── test_deepisles.py    # Tests for DeepISLES wrapper
```

### tests to write first (TDD order)

#### 1. `tests/inference/test_docker.py`

```python
"""Tests for Docker utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.exceptions import DockerNotAvailableError
from stroke_deepisles_demo.inference.docker import (
    build_docker_command,
    check_docker_available,
    ensure_docker_available,
    run_container,
)


class TestCheckDockerAvailable:
    """Tests for check_docker_available."""

    def test_returns_true_when_docker_responds(self) -> None:
        """Returns True when 'docker info' succeeds."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = check_docker_available()

            assert result is True

    def test_returns_false_when_docker_not_found(self) -> None:
        """Returns False when docker command not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = check_docker_available()

            assert result is False

    def test_returns_false_when_daemon_not_running(self) -> None:
        """Returns False when docker daemon not running."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            result = check_docker_available()

            assert result is False


class TestEnsureDockerAvailable:
    """Tests for ensure_docker_available."""

    def test_raises_when_docker_not_available(self) -> None:
        """Raises DockerNotAvailableError when Docker not available."""
        with patch(
            "stroke_deepisles_demo.inference.docker.check_docker_available",
            return_value=False,
        ):
            with pytest.raises(DockerNotAvailableError):
                ensure_docker_available()

    def test_no_error_when_docker_available(self) -> None:
        """No exception when Docker is available."""
        with patch(
            "stroke_deepisles_demo.inference.docker.check_docker_available",
            return_value=True,
        ):
            ensure_docker_available()  # Should not raise


class TestBuildDockerCommand:
    """Tests for build_docker_command."""

    def test_basic_command(self) -> None:
        """Builds basic docker run command."""
        cmd = build_docker_command("myimage:latest")

        assert cmd[0] == "docker"
        assert "run" in cmd
        assert "myimage:latest" in cmd

    def test_includes_rm_flag(self) -> None:
        """Includes --rm when remove=True."""
        cmd = build_docker_command("myimage", remove=True)

        assert "--rm" in cmd

    def test_excludes_rm_flag(self) -> None:
        """Excludes --rm when remove=False."""
        cmd = build_docker_command("myimage", remove=False)

        assert "--rm" not in cmd

    def test_includes_gpu_flag(self) -> None:
        """Includes --gpus all when gpu=True."""
        cmd = build_docker_command("myimage", gpu=True)

        assert "--gpus" in cmd
        gpu_index = cmd.index("--gpus")
        assert cmd[gpu_index + 1] == "all"

    def test_volume_mounts(self, temp_dir: Path) -> None:
        """Includes volume mounts."""
        volumes = {temp_dir: "/data"}
        cmd = build_docker_command("myimage", volumes=volumes)

        assert "-v" in cmd
        # Find the volume argument
        v_index = cmd.index("-v")
        assert f"{temp_dir}:/data" in cmd[v_index + 1]

    def test_custom_command(self) -> None:
        """Appends custom command arguments."""
        cmd = build_docker_command(
            "myimage", command=["--input", "/data", "--fast", "True"]
        )

        assert "--input" in cmd
        assert "--fast" in cmd


class TestRunContainer:
    """Tests for run_container."""

    def test_calls_subprocess_with_built_command(self) -> None:
        """Calls subprocess.run with built command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="output", stderr=""
            )
            with patch(
                "stroke_deepisles_demo.inference.docker.ensure_docker_available"
            ):
                run_container("myimage")

            mock_run.assert_called_once()

    def test_returns_result_with_exit_code(self) -> None:
        """Returns DockerRunResult with correct exit code."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=42, stdout="out", stderr="err"
            )
            with patch(
                "stroke_deepisles_demo.inference.docker.ensure_docker_available"
            ):
                result = run_container("myimage")

            assert result.exit_code == 42

    def test_captures_stdout_stderr(self) -> None:
        """Captures stdout and stderr from container."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="hello", stderr="warning"
            )
            with patch(
                "stroke_deepisles_demo.inference.docker.ensure_docker_available"
            ):
                result = run_container("myimage")

            assert result.stdout == "hello"
            assert result.stderr == "warning"

    def test_respects_timeout(self) -> None:
        """Passes timeout to subprocess."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with patch(
                "stroke_deepisles_demo.inference.docker.ensure_docker_available"
            ):
                run_container("myimage", timeout=60.0)

            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs.get("timeout") == 60.0


@pytest.mark.integration
class TestDockerIntegration:
    """Integration tests requiring real Docker."""

    def test_docker_actually_available(self) -> None:
        """Docker is actually available on this system."""
        # This test only runs with -m integration
        assert check_docker_available() is True

    def test_can_run_hello_world(self) -> None:
        """Can run docker hello-world container."""
        result = run_container("hello-world", timeout=60.0)

        assert result.exit_code == 0
        assert "Hello from Docker!" in result.stdout
```

#### 2. `tests/inference/test_deepisles.py`

```python
"""Tests for DeepISLES wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.exceptions import DeepISLESError, MissingInputError
from stroke_deepisles_demo.inference.deepisles import (
    DeepISLESResult,
    find_prediction_mask,
    run_deepisles_on_folder,
    validate_input_folder,
)


class TestValidateInputFolder:
    """Tests for validate_input_folder."""

    def test_succeeds_with_required_files(self, temp_dir: Path) -> None:
        """Returns paths when required files exist."""
        (temp_dir / "dwi.nii.gz").touch()
        (temp_dir / "adc.nii.gz").touch()

        dwi, adc, flair = validate_input_folder(temp_dir)

        assert dwi == temp_dir / "dwi.nii.gz"
        assert adc == temp_dir / "adc.nii.gz"
        assert flair is None

    def test_includes_flair_when_present(self, temp_dir: Path) -> None:
        """Returns FLAIR path when present."""
        (temp_dir / "dwi.nii.gz").touch()
        (temp_dir / "adc.nii.gz").touch()
        (temp_dir / "flair.nii.gz").touch()

        dwi, adc, flair = validate_input_folder(temp_dir)

        assert flair == temp_dir / "flair.nii.gz"

    def test_raises_when_dwi_missing(self, temp_dir: Path) -> None:
        """Raises MissingInputError when DWI is missing."""
        (temp_dir / "adc.nii.gz").touch()

        with pytest.raises(MissingInputError, match="dwi"):
            validate_input_folder(temp_dir)

    def test_raises_when_adc_missing(self, temp_dir: Path) -> None:
        """Raises MissingInputError when ADC is missing."""
        (temp_dir / "dwi.nii.gz").touch()

        with pytest.raises(MissingInputError, match="adc"):
            validate_input_folder(temp_dir)


class TestFindPredictionMask:
    """Tests for find_prediction_mask."""

    def test_finds_prediction_file(self, temp_dir: Path) -> None:
        """Finds prediction.nii.gz in output directory."""
        results_dir = temp_dir / "results"
        results_dir.mkdir()
        pred_file = results_dir / "prediction.nii.gz"
        pred_file.touch()

        result = find_prediction_mask(temp_dir)

        assert result == pred_file

    def test_raises_when_no_prediction(self, temp_dir: Path) -> None:
        """Raises DeepISLESError when no prediction found."""
        results_dir = temp_dir / "results"
        results_dir.mkdir()

        with pytest.raises(DeepISLESError, match="prediction"):
            find_prediction_mask(temp_dir)


class TestRunDeepIslesOnFolder:
    """Tests for run_deepisles_on_folder."""

    @pytest.fixture
    def valid_input_dir(self, temp_dir: Path) -> Path:
        """Create a valid input directory with required files."""
        (temp_dir / "dwi.nii.gz").touch()
        (temp_dir / "adc.nii.gz").touch()
        return temp_dir

    def test_validates_input_files(self, temp_dir: Path) -> None:
        """Validates input files before running Docker."""
        # Missing required files
        with pytest.raises(MissingInputError):
            run_deepisles_on_folder(temp_dir)

    def test_calls_docker_with_correct_image(self, valid_input_dir: Path) -> None:
        """Calls Docker with DeepISLES image."""
        with patch(
            "stroke_deepisles_demo.inference.deepisles.run_container"
        ) as mock_run:
            mock_run.return_value = MagicMock(exit_code=0, stdout="", stderr="")
            # Also mock finding the prediction
            with patch(
                "stroke_deepisles_demo.inference.deepisles.find_prediction_mask"
            ) as mock_find:
                mock_find.return_value = valid_input_dir / "results" / "pred.nii.gz"

                run_deepisles_on_folder(valid_input_dir)

            # Check image name
            call_args = mock_run.call_args
            assert "isleschallenge/deepisles" in str(call_args)

    def test_passes_fast_flag(self, valid_input_dir: Path) -> None:
        """Passes --fast True when fast=True."""
        with patch(
            "stroke_deepisles_demo.inference.deepisles.run_container"
        ) as mock_run:
            mock_run.return_value = MagicMock(exit_code=0, stdout="", stderr="")
            with patch(
                "stroke_deepisles_demo.inference.deepisles.find_prediction_mask"
            ) as mock_find:
                mock_find.return_value = valid_input_dir / "results" / "pred.nii.gz"

                run_deepisles_on_folder(valid_input_dir, fast=True)

            # Check --fast in command
            call_kwargs = mock_run.call_args.kwargs
            command = call_kwargs.get("command", [])
            assert "--fast" in command

    def test_raises_on_docker_failure(self, valid_input_dir: Path) -> None:
        """Raises DeepISLESError when Docker returns non-zero."""
        with patch(
            "stroke_deepisles_demo.inference.deepisles.run_container"
        ) as mock_run:
            mock_run.return_value = MagicMock(
                exit_code=1, stdout="", stderr="Segmentation fault"
            )

            with pytest.raises(DeepISLESError, match="failed"):
                run_deepisles_on_folder(valid_input_dir)

    def test_returns_result_with_prediction_path(self, valid_input_dir: Path) -> None:
        """Returns DeepISLESResult with prediction path."""
        with patch(
            "stroke_deepisles_demo.inference.deepisles.run_container"
        ) as mock_run:
            mock_run.return_value = MagicMock(exit_code=0, stdout="", stderr="")
            with patch(
                "stroke_deepisles_demo.inference.deepisles.find_prediction_mask"
            ) as mock_find:
                expected_path = valid_input_dir / "results" / "prediction.nii.gz"
                mock_find.return_value = expected_path

                result = run_deepisles_on_folder(valid_input_dir)

            assert isinstance(result, DeepISLESResult)
            assert result.prediction_path == expected_path


@pytest.mark.integration
@pytest.mark.slow
class TestDeepIslesIntegration:
    """Integration tests requiring real Docker and DeepISLES image."""

    def test_real_inference(self, synthetic_case_files) -> None:
        """Run actual DeepISLES inference on synthetic data."""
        # This test requires:
        # 1. Docker available
        # 2. isleschallenge/deepisles image pulled
        # 3. GPU (optional but recommended)
        #
        # Run with: pytest -m "integration and slow"

        from stroke_deepisles_demo.data.staging import stage_case_for_deepisles

        # Stage the synthetic files
        staged = stage_case_for_deepisles(
            synthetic_case_files,
            Path("/tmp/deepisles_test"),
        )

        # Run inference
        result = run_deepisles_on_folder(
            staged.input_dir,
            fast=True,
            gpu=False,  # Might not have GPU in CI
            timeout=600,
        )

        # Verify output exists
        assert result.prediction_path.exists()
```

### what to mock

- `subprocess.run` - Mock for all unit tests
- `check_docker_available` - Mock to control Docker availability
- `run_container` - Mock in DeepISLES tests to avoid Docker
- File system for prediction finding - Use temp directories

### what to test for real

- Command building (no subprocess needed)
- Input validation (real file system with temp dirs)
- Integration test: actual Docker hello-world
- Integration test: actual DeepISLES inference (marked `slow`)

## "done" criteria

Phase 2 is complete when:

1. All unit tests pass: `uv run pytest tests/inference/ -v`
2. Can build Docker commands correctly
3. Can validate input folders
4. Unit tests don't require Docker (all mocked)
5. Integration test passes with Docker: `uv run pytest -m integration tests/inference/`
6. Type checking passes: `uv run mypy src/stroke_deepisles_demo/inference/`
7. Code coverage for inference module > 80%

## implementation notes

- Check DeepISLES repo for exact output file names/structure
- Consider `--gpus all` vs `--gpus '"device=0"'` for GPU selection
- Timeout should be generous (30+ minutes) for full ensemble mode
- Log Docker stdout/stderr for debugging
- Consider streaming Docker output for long-running inference

### critical: docker file permissions (linux)

**Reviewer feedback (valid)**: Docker containers run as root by default on Linux. Output files written to mounted volumes will be owned by root:root. The Python process running as a normal user will fail to read or delete these files.

**Solution**: Pass `--user` flag to match host user:

```python
def build_docker_command(
    image: str,
    *,
    volumes: dict[Path, str] | None = None,
    gpu: bool = False,
    remove: bool = True,
    match_user: bool = True,  # NEW: default True on Linux
) -> list[str]:
    """Build docker run command."""
    cmd = ["docker", "run"]

    if remove:
        cmd.append("--rm")

    if gpu:
        cmd.extend(["--gpus", "all"])

    # Match host user to avoid permission issues
    if match_user and sys.platform != "darwin":  # Not needed on macOS
        import os
        uid = os.getuid()
        gid = os.getgid()
        cmd.extend(["--user", f"{uid}:{gid}"])

    if volumes:
        for host_path, container_path in volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])

    cmd.append(image)
    return cmd
```

Alternative: Fix permissions after Docker completes (less clean but works):

```python
def fix_docker_output_permissions(output_dir: Path) -> None:
    """Fix permissions on Docker-created files."""
    import subprocess
    # Only needed if running as non-root and files are root-owned
    try:
        subprocess.run(
            ["sudo", "chown", "-R", f"{os.getuid()}:{os.getgid()}", str(output_dir)],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # sudo not available or not needed
```

### critical: gpu availability check

**Reviewer feedback (valid)**: We check for Docker daemon but not NVIDIA Container Runtime. A user might have Docker but lack GPU passthrough setup.

**Solution**: Add GPU-specific availability check:

```python
def check_nvidia_docker_available() -> bool:
    """
    Check if NVIDIA Container Runtime is available for GPU support.

    Returns:
        True if nvidia-docker/nvidia-container-toolkit is configured
    """
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "--gpus", "all", "nvidia/cuda:11.0-base", "nvidia-smi"],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def ensure_gpu_available_if_requested(gpu: bool) -> None:
    """
    Verify GPU is available if requested, or warn user.

    Raises:
        DockerGPUNotAvailableError: If GPU requested but not available
    """
    if gpu and not check_nvidia_docker_available():
        raise DockerGPUNotAvailableError(
            "GPU requested but NVIDIA Container Runtime not available. "
            "Either install nvidia-container-toolkit or set gpu=False."
        )
```

Add to exceptions:

```python
class DockerGPUNotAvailableError(StrokeDemoError):
    """GPU requested but NVIDIA Container Runtime not available."""
```

### nifti orientation (medium risk)

**Reviewer feedback (noted)**: DeepISLES may expect specific anatomical orientation (e.g., RAS). BIDS data might be in different orientations.

**Mitigation**: DeepISLES is trained on ISLES challenge data which follows standard conventions. If issues arise, add orientation checking in staging:

```python
def check_nifti_orientation(nifti_path: Path) -> str:
    """Check NIfTI orientation code (e.g., 'RAS', 'LPS')."""
    import nibabel as nib
    img = nib.load(nifti_path)
    return nib.aff2axcodes(img.affine)

def conform_to_ras(nifti_path: Path, output_path: Path) -> Path:
    """Reorient NIfTI to RAS if needed."""
    import nibabel as nib
    img = nib.load(nifti_path)
    # nibabel can reorient - implement if needed
    ...
```

## dependencies to add

None - all covered in Phase 0.
