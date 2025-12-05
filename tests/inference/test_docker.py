"""Tests for Docker utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from stroke_deepisles_demo.core.exceptions import DockerNotAvailableError
from stroke_deepisles_demo.inference.docker import (
    build_docker_command,
    check_docker_available,
    ensure_docker_available,
    run_container,
)

if TYPE_CHECKING:
    from pathlib import Path


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
        with (
            patch(
                "stroke_deepisles_demo.inference.docker.check_docker_available",
                return_value=False,
            ),
            pytest.raises(DockerNotAvailableError),
        ):
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
        cmd = build_docker_command("myimage", command=["--input", "/data", "--fast", "True"])

        assert "--input" in cmd
        assert "--fast" in cmd

    def test_match_user_on_linux(self) -> None:
        """Adds --user flag on Linux when match_user=True."""
        # Use create=True to allow mocking os.getuid/getgid on platforms where they don't exist
        with (
            patch("os.name", "posix"),
            patch("sys.platform", "linux"),
            patch("os.getuid", return_value=1000, create=True),
            patch("os.getgid", return_value=1000, create=True),
        ):
            cmd = build_docker_command("myimage", match_user=True)
            assert "--user" in cmd
            assert "1000:1000" in cmd

    def test_no_match_user_on_mac(self) -> None:
        """Does NOT add --user flag on Darwin."""
        with patch("sys.platform", "darwin"):
            cmd = build_docker_command("myimage", match_user=True)
            assert "--user" not in cmd


class TestRunContainer:
    """Tests for run_container."""

    def test_calls_subprocess_with_built_command(self) -> None:
        """Calls subprocess.run with built command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
            with patch("stroke_deepisles_demo.inference.docker.ensure_docker_available"):
                run_container("myimage")

            mock_run.assert_called_once()

    def test_returns_result_with_exit_code(self) -> None:
        """Returns DockerRunResult with correct exit code."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=42, stdout="out", stderr="err")
            with patch("stroke_deepisles_demo.inference.docker.ensure_docker_available"):
                result = run_container("myimage")

            assert result.exit_code == 42

    def test_captures_stdout_stderr(self) -> None:
        """Captures stdout and stderr from container."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="warning")
            with patch("stroke_deepisles_demo.inference.docker.ensure_docker_available"):
                result = run_container("myimage")

            assert result.stdout == "hello"
            assert result.stderr == "warning"

    def test_respects_timeout(self) -> None:
        """Passes timeout to subprocess."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with patch("stroke_deepisles_demo.inference.docker.ensure_docker_available"):
                run_container("myimage", timeout=60.0)

            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs.get("timeout") == 60.0


@pytest.mark.integration
class TestDockerIntegration:
    """Integration tests requiring real Docker."""

    def test_docker_actually_available(self) -> None:
        """Docker is actually available on this system."""
        # This test only runs with -m integration
        # We skip if docker check fails, rather than failing the test
        available = check_docker_available()
        if not available:
            pytest.skip("Docker not available")

        assert available is True

    def test_can_run_hello_world(self) -> None:
        """Can run docker hello-world container."""
        if not check_docker_available():
            pytest.skip("Docker not available")

        result = run_container("hello-world", timeout=60.0)

        assert result.exit_code == 0
        assert "Hello from Docker!" in result.stdout
