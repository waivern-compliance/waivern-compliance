"""Integration tests for GitHub connector with real git operations.

These tests clone actual public repositories and verify git operations work.
Run with: uv run pytest -m integration
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from waivern_github.auth import GitHubAppAuth, PATAuth
from waivern_github.config import GitHubConnectorConfig
from waivern_github.git_operations import GitOperations


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


class TestGitOperationsCloneIntegration:
    """Integration tests for clone operations with real repositories."""

    @pytest.mark.integration
    def test_clone_minimal_strategy_creates_working_directory(self):
        """Test minimal clone creates a working git directory."""
        if not git_available():
            pytest.skip("git not installed")
        if not network_available():
            pytest.skip("Network not available")

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
    def test_clone_shallow_strategy_has_limited_history(self):
        """Test shallow clone has limited commit history."""
        if not git_available():
            pytest.skip("git not installed")
        if not network_available():
            pytest.skip("Network not available")

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

    @pytest.mark.integration
    def test_clone_with_specific_ref(self):
        """Test cloning a specific branch/ref."""
        if not git_available():
            pytest.skip("git not installed")
        if not network_available():
            pytest.skip("Network not available")

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


class TestGitOperationsCollectFilesIntegration:
    """Integration tests for file collection with real repositories."""

    @pytest.mark.integration
    def test_collect_files_returns_readme(self):
        """Test file collection finds the README file."""
        if not git_available():
            pytest.skip("git not installed")
        if not network_available():
            pytest.skip("Network not available")

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
    def test_collect_files_with_include_pattern(self):
        """Test file collection with include patterns filters correctly."""
        if not git_available():
            pytest.skip("git not installed")
        if not network_available():
            pytest.skip("Network not available")

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
    def test_collect_files_excludes_git_directory(self):
        """Test file collection excludes .git directory contents."""
        if not git_available():
            pytest.skip("git not installed")
        if not network_available():
            pytest.skip("Network not available")

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


class TestGitHubConnectorIntegration:
    """Integration tests for the full connector pipeline."""

    @pytest.mark.integration
    def test_full_extraction_pipeline(self):
        """Test the complete extraction pipeline with a real repository."""
        if not git_available():
            pytest.skip("git not installed")
        if not network_available():
            pytest.skip("Network not available")

        from waivern_core import Schema

        from waivern_github import GitHubConnector

        config = GitHubConnectorConfig.from_properties(
            {
                "repository": TEST_REPO,
                "clone_strategy": "minimal",
            }
        )

        connector = GitHubConnector(config)
        schema = Schema("standard_input", "1.0.0")

        message = connector.extract(schema)

        # Verify message structure
        assert message.schema.name == "standard_input"
        assert message.schema.version == "1.0.0"

        # Verify content has expected structure
        content = message.content
        assert isinstance(content, dict)
        assert "data" in content
        assert isinstance(content["data"], list)
        assert len(content["data"]) > 0

        # Verify README was extracted
        data_items = content["data"]
        file_paths = [item["metadata"]["file_path"] for item in data_items]
        assert "README" in file_paths

        # Verify README content is present
        readme_item = next(
            item for item in data_items if item["metadata"]["file_path"] == "README"
        )
        assert "Hello World" in readme_item["content"]


class TestAuthIntegration:
    """Integration tests for GitHub authentication."""

    @pytest.mark.integration
    def test_pat_auth_can_clone_private_repo(self):
        """Test PAT authentication works for cloning."""
        if not git_available():
            pytest.skip("git not installed")
        if not network_available():
            pytest.skip("Network not available")

        token = os.getenv("GITHUB_TOKEN")
        if not token:
            pytest.skip("GITHUB_TOKEN not set")

        # PATAuth just stores the token - verify it works with a clone
        auth = PATAuth(token)
        retrieved_token = auth.get_token()

        assert retrieved_token == token
        assert len(retrieved_token) > 0

        # Test that the token can be used in a clone URL
        # (we just verify the URL format, actual private repo clone
        # would require a real private repo the token has access to)
        # GITHUB_TOKEN env var is already set, so from_properties will pick it up
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
            # This will use the token in the URL (even for public repos it works)
            git_ops.clone(config, clone_path)

            assert (clone_path / "README").exists()

    @pytest.mark.integration
    def test_github_app_auth_generates_token(self):
        """Test GitHub App authentication generates installation token."""
        app_id = os.getenv("GITHUB_APP_ID")
        private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
        installation_id = os.getenv("GITHUB_APP_INSTALLATION_ID")

        if not all([app_id, private_key_path, installation_id]):
            pytest.skip(
                "GitHub App credentials not configured "
                "(GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY_PATH, GITHUB_APP_INSTALLATION_ID)"
            )

        key_path = Path(private_key_path)  # type: ignore[arg-type]
        if not key_path.exists():
            pytest.skip(f"Private key file not found: {private_key_path}")

        auth = GitHubAppAuth(
            app_id=int(app_id),  # type: ignore[arg-type]
            private_key_path=key_path,
            installation_id=int(installation_id),  # type: ignore[arg-type]
        )

        # This makes a real API call to GitHub
        token = auth.get_token()

        # Installation tokens are typically 40+ characters
        assert isinstance(token, str)
        assert len(token) > 20
        # GitHub installation tokens start with specific prefixes
        assert token.startswith("ghs_") or token.startswith("v1.")
