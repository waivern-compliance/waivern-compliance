"""Tests for git_operations module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waivern_github.config import GitHubConnectorConfig
from waivern_github.git_operations import GitOperations


def make_config(
    repository: str = "owner/repo",
    ref: str = "main",
    clone_strategy: str = "minimal",
    token: str | None = None,
    clone_timeout: int = 300,
) -> GitHubConnectorConfig:
    """Create a GitHubConnectorConfig for testing."""
    config = GitHubConnectorConfig.model_validate(
        {
            "repository": repository,
            "ref": ref,
            "clone_strategy": clone_strategy,
        }
    )
    # Set token via internal attribute (simulating env var loading)
    if token:
        object.__setattr__(config, "_token", token)
    # Override timeout if different from default
    if clone_timeout != 300:
        object.__setattr__(config, "clone_timeout", clone_timeout)
    return config


class TestGitOperationsClone:
    """Tests for GitOperations.clone() method - clone strategies."""

    def test_clone_minimal_strategy_builds_correct_command(
        self, tmp_path: Path
    ) -> None:
        """Test that minimal strategy uses --depth 1 --filter=blob:none --sparse."""
        git_ops = GitOperations()
        config = make_config(clone_strategy="minimal")

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.clone(config=config, target_dir=tmp_path)

        # Verify clone command
        clone_call = mock_run.call_args_list[0]
        clone_args = clone_call[0][0]

        assert "git" in clone_args
        assert "clone" in clone_args
        assert "--depth" in clone_args
        assert "1" in clone_args
        assert "--filter=blob:none" in clone_args
        assert "--sparse" in clone_args

    def test_clone_shallow_strategy_builds_correct_command(
        self, tmp_path: Path
    ) -> None:
        """Test that shallow strategy uses --depth 1 only."""
        git_ops = GitOperations()
        config = make_config(clone_strategy="shallow")

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.clone(config=config, target_dir=tmp_path)

        clone_args = mock_run.call_args_list[0][0][0]

        assert "--depth" in clone_args
        assert "1" in clone_args
        assert "--filter=blob:none" not in clone_args
        assert "--sparse" not in clone_args

    def test_clone_partial_strategy_builds_correct_command(
        self, tmp_path: Path
    ) -> None:
        """Test that partial strategy uses --filter=blob:none --sparse."""
        git_ops = GitOperations()
        config = make_config(clone_strategy="partial")

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.clone(config=config, target_dir=tmp_path)

        clone_args = mock_run.call_args_list[0][0][0]

        assert "--filter=blob:none" in clone_args
        assert "--sparse" in clone_args
        assert "--depth" not in clone_args

    def test_clone_full_strategy_builds_correct_command(self, tmp_path: Path) -> None:
        """Test that full clone has no special flags."""
        git_ops = GitOperations()
        config = make_config(clone_strategy="full")

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.clone(config=config, target_dir=tmp_path)

        clone_args = mock_run.call_args_list[0][0][0]

        assert "--depth" not in clone_args
        assert "--filter=blob:none" not in clone_args
        assert "--sparse" not in clone_args
        assert "clone" in clone_args  # Still a clone command


class TestGitOperationsAuth:
    """Tests for GitOperations.clone() method - authentication."""

    def test_clone_with_token_includes_auth_in_url(self, tmp_path: Path) -> None:
        """Test that token is embedded in clone URL for private repos."""
        git_ops = GitOperations()
        config = make_config(token="ghp_secret_token")  # noqa: S106 - test token

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.clone(config=config, target_dir=tmp_path)

        clone_args = mock_run.call_args_list[0][0][0]
        clone_url = [arg for arg in clone_args if "github.com" in arg][0]

        assert "x-access-token:ghp_secret_token@github.com" in clone_url

    def test_clone_without_token_uses_plain_url(self, tmp_path: Path) -> None:
        """Test that no auth in URL for public repos."""
        git_ops = GitOperations()
        config = make_config(token=None)

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.clone(config=config, target_dir=tmp_path)

        clone_args = mock_run.call_args_list[0][0][0]
        clone_url = [arg for arg in clone_args if "github.com" in arg][0]

        assert clone_url == "https://github.com/owner/repo.git"
        assert "x-access-token" not in clone_url


class TestGitOperationsRef:
    """Tests for GitOperations.clone() method - ref checkout."""

    def test_clone_checks_out_specified_ref(self, tmp_path: Path) -> None:
        """Test that clone checks out the specified ref after cloning."""
        git_ops = GitOperations()
        config = make_config(ref="feature/my-branch")

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            git_ops.clone(config=config, target_dir=tmp_path)

        # Second call should be checkout
        assert len(mock_run.call_args_list) == 2
        checkout_args = mock_run.call_args_list[1][0][0]

        assert "git" in checkout_args
        assert "checkout" in checkout_args
        assert "feature/my-branch" in checkout_args


class TestGitOperationsErrors:
    """Tests for GitOperations error handling."""

    def test_clone_raises_error_on_failure(self, tmp_path: Path) -> None:
        """Test that git failures raise exception with stderr message."""
        import subprocess

        git_ops = GitOperations()
        config = make_config(repository="owner/nonexistent")

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", "clone"],
                stderr=b"fatal: repository not found",
            )

            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                git_ops.clone(config=config, target_dir=tmp_path)

            assert exc_info.value.returncode == 128
            assert b"repository not found" in exc_info.value.stderr

    def test_clone_raises_error_on_timeout(self, tmp_path: Path) -> None:
        """Test that timeout raises appropriate exception."""
        import subprocess

        git_ops = GitOperations()
        config = make_config(clone_timeout=300)

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["git", "clone"],
                timeout=300,
            )

            with pytest.raises(subprocess.TimeoutExpired) as exc_info:
                git_ops.clone(config=config, target_dir=tmp_path)

            assert exc_info.value.timeout == 300


class TestGitOperationsSparseCheckout:
    """Tests for GitOperations.sparse_checkout() method."""

    def test_sparse_checkout_sets_patterns(self, tmp_path: Path) -> None:
        """Test that sparse-checkout runs with provided patterns."""
        git_ops = GitOperations()

        with patch("waivern_github.git_operations.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            git_ops.sparse_checkout(
                repo_dir=tmp_path,
                patterns=["src/", "tests/", "*.md"],
            )

        # Verify sparse-checkout set command was called with patterns
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]

        assert "git" in call_args
        assert "sparse-checkout" in call_args
        assert "set" in call_args
        assert "src/" in call_args
        assert "tests/" in call_args
        assert "*.md" in call_args


class TestGitOperationsCollectFiles:
    """Tests for GitOperations.collect_files() method."""

    def test_collect_files_returns_all_files_without_patterns(
        self, tmp_path: Path
    ) -> None:
        """Test that all files are returned when no patterns specified."""
        # Create a simple directory structure
        (tmp_path / "file1.py").write_text("content1")
        (tmp_path / "file2.md").write_text("content2")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("content3")

        git_ops = GitOperations()

        result = git_ops.collect_files(
            repo_dir=tmp_path,
            include_patterns=None,
            exclude_patterns=None,
            max_files=100,
        )

        # Should return all 3 files
        assert len(result) == 3
        filenames = {f.name for f in result}
        assert "file1.py" in filenames
        assert "file2.md" in filenames
        assert "main.py" in filenames

    def test_collect_files_with_include_patterns_filters_correctly(
        self, tmp_path: Path
    ) -> None:
        """Test that only matching files are returned with include patterns."""
        # Create a mixed directory structure
        (tmp_path / "main.py").write_text("python")
        (tmp_path / "utils.py").write_text("python")
        (tmp_path / "readme.md").write_text("markdown")
        (tmp_path / "config.yaml").write_text("yaml")

        git_ops = GitOperations()

        result = git_ops.collect_files(
            repo_dir=tmp_path,
            include_patterns=["*.py"],
            exclude_patterns=None,
            max_files=100,
        )

        # Should return only .py files
        assert len(result) == 2
        filenames = {f.name for f in result}
        assert filenames == {"main.py", "utils.py"}

    def test_collect_files_with_exclude_patterns_filters_correctly(
        self, tmp_path: Path
    ) -> None:
        """Test that non-matching files are returned with exclude patterns."""
        # Create a mixed directory structure
        (tmp_path / "main.py").write_text("python")
        (tmp_path / "test_main.py").write_text("test")
        (tmp_path / "readme.md").write_text("markdown")

        git_ops = GitOperations()

        result = git_ops.collect_files(
            repo_dir=tmp_path,
            include_patterns=None,
            exclude_patterns=["test_*.py"],
            max_files=100,
        )

        # Should return all files except test_*.py
        assert len(result) == 2
        filenames = {f.name for f in result}
        assert filenames == {"main.py", "readme.md"}

    def test_collect_files_respects_max_files_limit(self, tmp_path: Path) -> None:
        """Test that collection stops at max_files limit."""
        # Create more files than the limit
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text(f"content{i}")

        git_ops = GitOperations()

        result = git_ops.collect_files(
            repo_dir=tmp_path,
            include_patterns=None,
            exclude_patterns=None,
            max_files=3,
        )

        # Should return exactly 3 files
        assert len(result) == 3

    def test_collect_files_returns_only_files_not_directories(
        self, tmp_path: Path
    ) -> None:
        """Test that directories are not included in results."""
        # Create a structure with files and directories
        (tmp_path / "file.py").write_text("content")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("module")
        (tmp_path / "tests").mkdir()  # Empty directory

        git_ops = GitOperations()

        result = git_ops.collect_files(
            repo_dir=tmp_path,
            include_patterns=None,
            exclude_patterns=None,
            max_files=100,
        )

        # Should return only files, not directories
        assert len(result) == 2
        for path in result:
            assert path.is_file()
            assert not path.is_dir()
