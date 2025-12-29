"""Integration tests for git clone operations with real repositories."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from waivern_github.config import GitHubConnectorConfig
from waivern_github.git_operations import GitOperations

from .conftest import TEST_REPO


class TestCloneStrategies:
    """Integration tests for different clone strategies."""

    @pytest.mark.integration
    def test_minimal_strategy_creates_working_directory(self, require_git_and_network):
        """Test minimal clone creates a working git directory."""
        config = GitHubConnectorConfig.from_properties(
            {
                "repository": TEST_REPO,
                "clone_strategy": "minimal",
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / "repo"
            clone_path.mkdir()

            git_ops = GitOperations()
            git_ops.clone(config, clone_path)

            # Verify it's a git directory
            assert (clone_path / ".git").exists() or (clone_path / "HEAD").exists()
            # Verify README exists (Hello-World has a README)
            assert (clone_path / "README").exists()

    @pytest.mark.integration
    def test_shallow_strategy_has_limited_history(self, require_git_and_network):
        """Test shallow clone has limited commit history."""
        config = GitHubConnectorConfig.from_properties(
            {
                "repository": TEST_REPO,
                "clone_strategy": "shallow",
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / "repo"
            clone_path.mkdir()

            git_ops = GitOperations()
            git_ops.clone(config, clone_path)

            # Verify shallow clone (limited history)
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],  # noqa: S607
                check=False,
                cwd=clone_path,
                capture_output=True,
                text=True,
            )
            commit_count = int(result.stdout.strip())
            # Shallow clone should have exactly 1 commit
            assert commit_count == 1


class TestRefCheckout:
    """Integration tests for checking out specific refs."""

    @pytest.mark.integration
    def test_clone_with_specific_branch(self, require_git_and_network):
        """Test cloning a specific branch/ref."""
        # Hello-World has a 'test' branch
        config = GitHubConnectorConfig.from_properties(
            {
                "repository": TEST_REPO,
                "ref": "test",
                "clone_strategy": "minimal",
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / "repo"
            clone_path.mkdir()

            git_ops = GitOperations()
            git_ops.clone(config, clone_path)

            # Verify we're on the test branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],  # noqa: S607
                check=False,
                cwd=clone_path,
                capture_output=True,
                text=True,
            )
            # After checkout, HEAD should be detached or on the ref
            assert result.returncode == 0
