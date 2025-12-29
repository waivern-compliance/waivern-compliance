"""Shared fixtures for GitHub connector integration tests.

These tests require network access and git to be installed.
Run with: uv run pytest -m integration
"""

import shutil
import subprocess

import pytest


def git_available() -> bool:
    """Check if git is available on the system."""
    return shutil.which("git") is not None


def network_available() -> bool:
    """Check if network is available by testing GitHub connectivity."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "https://github.com/octocat/Hello-World.git", "HEAD"],  # noqa: S607
            check=False,
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Use a minimal, stable public repo for testing
TEST_REPO = "octocat/Hello-World"


@pytest.fixture
def require_git_and_network():
    """Skip test if git or network is unavailable."""
    if not git_available():
        pytest.skip("git not installed")
    if not network_available():
        pytest.skip("Network not available")
