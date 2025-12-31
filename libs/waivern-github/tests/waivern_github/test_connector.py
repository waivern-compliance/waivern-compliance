"""Tests for GitHub connector."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from waivern_core import Schema
from waivern_core.errors import ConnectorConfigError, ConnectorExtractionError

from waivern_github.config import GitHubConnectorConfig
from waivern_github.connector import GitHubConnector


# Helper to create test configs
def make_config(  # noqa: PLR0913 - test helper with many optional params
    repository: str = "owner/repo",
    ref: str = "main",
    clone_strategy: str = "minimal",
    token: str | None = None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    max_files: int = 1000,
) -> GitHubConnectorConfig:
    """Create a GitHubConnectorConfig for testing."""
    config = GitHubConnectorConfig.model_validate(
        {
            "repository": repository,
            "ref": ref,
            "clone_strategy": clone_strategy,
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "max_files": max_files,
        }
    )
    if token:
        object.__setattr__(config, "_token", token)
    return config


class TestGitHubConnectorMetadata:
    """Tests for connector class metadata methods."""

    def test_get_name_returns_github(self) -> None:
        """get_name returns 'github' as the connector identifier."""
        assert GitHubConnector.get_name() == "github"

    def test_get_supported_output_schemas_returns_standard_input(self) -> None:
        """get_supported_output_schemas returns standard_input v1.0.0."""
        schemas = GitHubConnector.get_supported_output_schemas()

        assert len(schemas) == 1
        assert schemas[0].name == "standard_input"
        assert schemas[0].version == "1.0.0"


class TestGitHubConnectorExtraction:
    """Tests for GitHub data extraction."""

    def test_extract_returns_message_with_correct_schema(self, tmp_path: Path) -> None:
        """Extract returns a Message with the requested output schema."""
        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            result = connector.extract(Schema("standard_input", "1.0.0"))

        assert result.schema is not None
        assert result.schema.name == "standard_input"
        assert result.schema.version == "1.0.0"

    def test_extract_clones_repository_with_config(self, tmp_path: Path) -> None:
        """Extract calls GitOperations.clone() with the config."""
        config = make_config(repository="myorg/myrepo", ref="develop")
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        mock_git_ops.clone.assert_called_once()
        call_args = mock_git_ops.clone.call_args
        assert call_args[0][0] == config  # First arg is config

    def test_extract_collects_files_with_patterns(self, tmp_path: Path) -> None:
        """Extract calls collect_files() with include patterns."""
        config = make_config(
            include_patterns=["*.py", "*.md"],
            max_files=500,
        )
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        mock_git_ops.collect_files.assert_called_once_with(
            repo_dir=tmp_path,
            include_patterns=["*.py", "*.md"],
            exclude_patterns=None,
            max_files=500,
        )

    def test_extract_reads_file_contents(self, tmp_path: Path) -> None:
        """File content appears in extracted data items."""
        # Create a test file
        test_file = tmp_path / "hello.py"
        test_file.write_text("print('hello world')")

        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = [test_file]

            result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        assert len(data) == 1
        assert data[0]["content"] == "print('hello world')"

    def test_extract_creates_temp_directory_and_cleans_up(self, tmp_path: Path) -> None:
        """Temp directory is created for clone and removed after extraction."""
        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree") as mock_rmtree,
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        mock_mkdtemp.assert_called_once()
        mock_rmtree.assert_called_once_with(str(tmp_path), ignore_errors=True)

    def test_extract_handles_empty_repository(self, tmp_path: Path) -> None:
        """Empty data list when no files match patterns."""
        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            result = connector.extract(Schema("standard_input", "1.0.0"))

        assert result.content.get("data", []) == []

    def test_extract_respects_max_files_limit(self, tmp_path: Path) -> None:
        """Only processes up to max_files files."""
        config = make_config(max_files=2)
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        # Verify max_files was passed to collect_files
        call_kwargs = mock_git_ops.collect_files.call_args[1]
        assert call_kwargs["max_files"] == 2

    def test_extract_raises_error_for_unsupported_schema(self) -> None:
        """ConnectorConfigError is raised for unsupported output schema."""
        config = make_config()
        connector = GitHubConnector(config)

        with pytest.raises(ConnectorConfigError, match="Unsupported.*schema"):
            connector.extract(Schema("unsupported_schema", "1.0.0"))

    def test_extract_raises_error_on_clone_failure(self, tmp_path: Path) -> None:
        """ConnectorExtractionError is raised when clone fails."""
        import subprocess

        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.clone.side_effect = subprocess.CalledProcessError(
                128, "git clone", stderr=b"repository not found"
            )

            with pytest.raises(ConnectorExtractionError):
                connector.extract(Schema("standard_input", "1.0.0"))


class TestGitHubConnectorDataItems:
    """Tests for granular data item extraction."""

    def test_creates_data_item_for_each_file(self, tmp_path: Path) -> None:
        """Each file becomes a separate data item."""
        # Create test files
        (tmp_path / "file1.py").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "file3.py").write_text("content3")

        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = [
                tmp_path / "file1.py",
                tmp_path / "file2.py",
                tmp_path / "file3.py",
            ]

            result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        assert len(data) == 3

    def test_data_item_content_is_file_content(self, tmp_path: Path) -> None:
        """Data item content field contains the file text."""
        test_content = "def hello():\n    return 'world'"
        (tmp_path / "module.py").write_text(test_content)

        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = [tmp_path / "module.py"]

            result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        assert data[0]["content"] == test_content

    def test_data_item_metadata_includes_file_path(self, tmp_path: Path) -> None:
        """Data item metadata includes the file_path field."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("main")

        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = [tmp_path / "src" / "main.py"]

            result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        assert data[0]["metadata"]["file_path"] == "src/main.py"

    def test_data_item_source_follows_github_uri_format(self, tmp_path: Path) -> None:
        """Data item source is formatted as github://owner/repo@ref/path."""
        (tmp_path / "app.py").write_text("app")

        config = make_config(repository="myorg/myrepo", ref="v1.0.0")
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = [tmp_path / "app.py"]

            result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        assert data[0]["metadata"]["source"] == "github://myorg/myrepo@v1.0.0/app.py"

    def test_data_item_connector_type_is_github(self, tmp_path: Path) -> None:
        """Data item connector_type is 'github'."""
        (tmp_path / "test.py").write_text("test")

        config = make_config()
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = [tmp_path / "test.py"]

            result = connector.extract(Schema("standard_input", "1.0.0"))

        data = result.content.get("data", [])
        assert data[0]["metadata"]["connector_type"] == "github"


class TestSparseCheckoutBehaviour:
    """Tests for sparse checkout behaviour with different strategies."""

    def test_minimal_strategy_calls_sparse_checkout_with_directory_paths(
        self, tmp_path: Path
    ) -> None:
        """Minimal strategy calls sparse_checkout with directory paths, not globs."""
        config = make_config(
            clone_strategy="minimal",
            include_patterns=["libs/waivern/tests/*.py", "src/components/*.tsx"],
        )
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        # sparse_checkout should be called with directory paths (no globs)
        mock_git_ops.sparse_checkout.assert_called_once()
        call_args = mock_git_ops.sparse_checkout.call_args[0]
        patterns = call_args[1]
        # Should contain directory paths without wildcards
        assert all("*" not in p for p in patterns)
        assert set(patterns) == {"libs/waivern/tests", "src/components"}

    def test_shallow_strategy_does_not_call_sparse_checkout(
        self, tmp_path: Path
    ) -> None:
        """Shallow strategy does not call sparse_checkout."""
        config = make_config(
            clone_strategy="shallow",
            include_patterns=["libs/**/*.py"],
        )
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        mock_git_ops.sparse_checkout.assert_not_called()

    def test_full_strategy_does_not_call_sparse_checkout(self, tmp_path: Path) -> None:
        """Full strategy does not call sparse_checkout."""
        config = make_config(
            clone_strategy="full",
            include_patterns=["src/*.py"],
        )
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        mock_git_ops.sparse_checkout.assert_not_called()

    def test_no_sparse_checkout_without_include_patterns(self, tmp_path: Path) -> None:
        """No sparse_checkout call when include_patterns is not set."""
        config = make_config(clone_strategy="minimal", include_patterns=None)
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        mock_git_ops.sparse_checkout.assert_not_called()


class TestGitHubConnectorAuth:
    """Tests for authentication handling."""

    def test_extract_uses_token_from_config(self, tmp_path: Path) -> None:
        """Token from config is available during clone operation."""
        config = make_config(token="ghp_test_token")  # noqa: S106 - test token
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            connector.extract(Schema("standard_input", "1.0.0"))

        # Verify clone was called with config that has token
        call_args = mock_git_ops.clone.call_args
        passed_config = call_args[0][0]
        assert passed_config.token == "ghp_test_token"  # noqa: S105 - test token

    def test_extract_works_without_token(self, tmp_path: Path) -> None:
        """Clone works with token=None for public repos."""
        config = make_config(token=None)
        connector = GitHubConnector(config)

        with (
            patch("waivern_github.connector.GitOperations") as mock_git_ops_class,
            patch("waivern_github.connector.tempfile.mkdtemp") as mock_mkdtemp,
            patch("waivern_github.connector.shutil.rmtree"),
        ):
            mock_mkdtemp.return_value = str(tmp_path)
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_git_ops.collect_files.return_value = []

            result = connector.extract(Schema("standard_input", "1.0.0"))

        # Should complete successfully without token
        assert result.schema is not None
        call_args = mock_git_ops.clone.call_args
        passed_config = call_args[0][0]
        assert passed_config.token is None
