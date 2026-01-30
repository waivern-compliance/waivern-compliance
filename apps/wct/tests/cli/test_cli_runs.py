"""CLI tests for 'wct runs' command."""

import os
import re
import subprocess
from pathlib import Path

import pytest


class TestWCTRunsCommand:
    """Tests for 'wct runs' CLI command."""

    @pytest.fixture
    def store_env(self, tmp_path: Path) -> dict[str, str]:
        """Create environment with temporary filesystem store.

        This ensures tests don't interfere with real runs and are isolated.
        """
        env = os.environ.copy()
        env["WAIVERN_STORE_TYPE"] = "filesystem"
        env["WAIVERN_STORE_PATH"] = str(tmp_path / ".waivern")
        return env

    def test_runs_command_lists_recorded_runs(
        self, tmp_path: Path, store_env: dict[str, str]
    ) -> None:
        """Lists all recorded runs with metadata after executing a runbook."""
        # Arrange - Execute a runbook to create a run
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")
        assert runbook_path.exists(), f"Runbook not found: {runbook_path}"

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Execute runbook to create a run
        run_result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "wct",
                "run",
                str(runbook_path),
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env=store_env,
        )
        assert run_result.returncode == 0, f"Setup failed: {run_result.stderr}"

        # Act - List runs
        result = subprocess.run(
            ["uv", "run", "wct", "runs"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=store_env,
        )

        # Assert
        assert result.returncode == 0, (
            f"wct runs failed with return code {result.returncode}.\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
        # Table title should be present
        assert "Recorded Runs" in result.stdout
        # Should show a truncated UUID pattern (8 chars + ...)
        assert re.search(r"[a-f0-9]{8}\.\.\.", result.stdout), (
            "Expected truncated run ID (UUID pattern) in output"
        )
        # Status column should show 'completed'
        assert "completed" in result.stdout

    def test_runs_command_filters_by_status(
        self, tmp_path: Path, store_env: dict[str, str]
    ) -> None:
        """Filters runs by status when --status flag is provided."""
        # Arrange - Execute a runbook to create a completed run
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")
        assert runbook_path.exists(), f"Runbook not found: {runbook_path}"

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Execute runbook to create a completed run
        run_result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "wct",
                "run",
                str(runbook_path),
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env=store_env,
        )
        assert run_result.returncode == 0, f"Setup failed: {run_result.stderr}"

        # Act - List runs with status filter for 'completed'
        result_completed = subprocess.run(
            ["uv", "run", "wct", "runs", "--status", "completed"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=store_env,
        )

        # Act - List runs with status filter for 'failed' (should be empty)
        result_failed = subprocess.run(
            ["uv", "run", "wct", "runs", "--status", "failed"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=store_env,
        )

        # Assert - completed filter shows the run
        assert result_completed.returncode == 0
        assert "Recorded Runs" in result_completed.stdout
        assert "completed" in result_completed.stdout

        # Assert - failed filter shows no runs (specific message)
        assert result_failed.returncode == 0
        assert "No runs with status 'failed'" in result_failed.stdout

    def test_runs_command_shows_message_when_no_runs(
        self, store_env: dict[str, str]
    ) -> None:
        """Shows informative message when no runs exist."""
        # Act - List runs (store is empty due to fixture)
        result = subprocess.run(
            ["uv", "run", "wct", "runs"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=store_env,
        )

        # Assert
        assert result.returncode == 0, (
            f"wct runs failed with return code {result.returncode}.\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
        # Should show the specific "no runs" message
        assert "No runs recorded" in result.stdout
