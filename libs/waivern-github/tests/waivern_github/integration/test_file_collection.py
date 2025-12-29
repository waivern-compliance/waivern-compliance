"""Integration tests for file collection with real repositories."""

import tempfile
from pathlib import Path

import pytest

from waivern_github.config import GitHubConnectorConfig
from waivern_github.git_operations import GitOperations

from .conftest import TEST_REPO


class TestFileCollection:
    """Integration tests for collecting files from cloned repositories."""

    @pytest.mark.integration
    def test_collect_files_returns_readme(self, require_git_and_network):
        """Test file collection finds the README file."""
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

            files = git_ops.collect_files(repo_dir=clone_path)

            # Should find the README file
            file_names = [f.name for f in files]
            assert "README" in file_names

    @pytest.mark.integration
    def test_collect_files_with_include_pattern(self, require_git_and_network):
        """Test file collection with include patterns filters correctly."""
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

            # Only include README
            files = git_ops.collect_files(
                repo_dir=clone_path,
                include_patterns=["README"],
            )

            # Should only find README
            assert len(files) == 1
            assert files[0].name == "README"

    @pytest.mark.integration
    def test_collect_files_excludes_git_directory(self, require_git_and_network):
        """Test file collection excludes .git directory contents."""
        config = GitHubConnectorConfig.from_properties(
            {
                "repository": TEST_REPO,
                "clone_strategy": "full",  # Full clone to ensure .git exists
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / "repo"
            clone_path.mkdir()

            git_ops = GitOperations()
            git_ops.clone(config, clone_path)

            files = git_ops.collect_files(repo_dir=clone_path)

            # No files should be from .git directory
            for f in files:
                assert ".git" not in str(f)
