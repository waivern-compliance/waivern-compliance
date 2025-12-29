"""Tests for GitHubConnectorConfig."""

import pytest
from waivern_core.errors import ConnectorConfigError

from waivern_github.config import GitHubConnectorConfig

GITHUB_ENV_VARS = [
    "GITHUB_TOKEN",
    "GITHUB_APP_ID",
    "GITHUB_PRIVATE_KEY_PATH",
    "GITHUB_INSTALLATION_ID",
]


class TestGitHubConnectorConfig:
    """Test GitHubConnectorConfig class."""

    def test_from_properties_with_minimal_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties applies correct defaults with minimal config."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        config = GitHubConnectorConfig.from_properties({"repository": "owner/repo"})

        assert config.repository == "owner/repo"
        assert config.ref == "HEAD"
        assert config.include_patterns is None
        assert config.exclude_patterns is None
        assert config.max_files == 1000
        assert config.clone_strategy == "minimal"
        assert config.clone_timeout == 300
        assert config.auth_method == "pat"
        assert config.token is None  # No GITHUB_TOKEN set

    def test_from_properties_with_full_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties respects all provided properties."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        config = GitHubConnectorConfig.from_properties(
            {
                "repository": "company/webapp",
                "ref": "main",
                "include_patterns": ["src/**/*.php"],
                "max_files": 500,
                "clone_strategy": "shallow",
                "clone_timeout": 600,
                "auth_method": "pat",
            }
        )

        assert config.repository == "company/webapp"
        assert config.ref == "main"
        assert config.include_patterns == ["src/**/*.php"]
        assert config.exclude_patterns is None
        assert config.max_files == 500
        assert config.clone_strategy == "shallow"
        assert config.clone_timeout == 600
        assert config.auth_method == "pat"
        assert config.token == "ghp_test_token"  # noqa: S105

    def test_from_properties_with_exclude_patterns(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties with exclude_patterns."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        config = GitHubConnectorConfig.from_properties(
            {
                "repository": "owner/repo",
                "exclude_patterns": ["*.md", "tests/**"],
            }
        )

        assert config.include_patterns is None
        assert config.exclude_patterns == ["*.md", "tests/**"]

    def test_from_properties_missing_repository_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties raises error when repository is missing."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(
            ConnectorConfigError, match="repository property is required"
        ):
            GitHubConnectorConfig.from_properties({})

    def test_from_properties_empty_repository_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties raises error when repository is empty."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(
            ConnectorConfigError, match="repository property is required"
        ):
            GitHubConnectorConfig.from_properties({"repository": ""})

    def test_from_properties_invalid_repository_format_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties raises error for invalid repository format."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConnectorConfigError, match="owner/repo"):
            GitHubConnectorConfig.from_properties({"repository": "invalid"})

    def test_from_properties_repository_with_only_slash_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties raises error for repository with only slash."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConnectorConfigError, match="owner/repo"):
            GitHubConnectorConfig.from_properties({"repository": "/"})

    def test_from_properties_mutual_exclusivity_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties raises error when both include and exclude patterns set."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConnectorConfigError, match="mutually exclusive"):
            GitHubConnectorConfig.from_properties(
                {
                    "repository": "owner/repo",
                    "include_patterns": ["*.php"],
                    "exclude_patterns": ["*.md"],
                }
            )

    def test_from_properties_uses_github_token_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties uses GITHUB_TOKEN environment variable."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret_token")

        config = GitHubConnectorConfig.from_properties({"repository": "owner/repo"})

        assert config.token == "ghp_secret_token"  # noqa: S105

    def test_from_properties_github_app_auth_with_all_env_vars(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Test from_properties with GitHub App authentication."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        # Create a dummy private key file
        key_file = tmp_path / "private-key.pem"
        key_file.write_text(
            "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
        )

        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", str(key_file))
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        config = GitHubConnectorConfig.from_properties(
            {"repository": "owner/repo", "auth_method": "app"}
        )

        assert config.auth_method == "app"
        assert config.app_id == 12345
        assert config.private_key_path == key_file
        assert config.installation_id == 67890

    def test_from_properties_github_app_missing_app_id_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties raises error when GITHUB_APP_ID is missing for app auth."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConnectorConfigError, match="GITHUB_APP_ID"):
            GitHubConnectorConfig.from_properties(
                {"repository": "owner/repo", "auth_method": "app"}
            )

    def test_from_properties_github_app_missing_private_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties raises error when GITHUB_PRIVATE_KEY_PATH is missing."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GITHUB_APP_ID", "12345")

        with pytest.raises(ConnectorConfigError, match="GITHUB_PRIVATE_KEY_PATH"):
            GitHubConnectorConfig.from_properties(
                {"repository": "owner/repo", "auth_method": "app"}
            )

    def test_from_properties_github_app_missing_installation_id_raises_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Test from_properties raises error when GITHUB_INSTALLATION_ID is missing."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        key_file = tmp_path / "private-key.pem"
        key_file.write_text("test key")

        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", str(key_file))

        with pytest.raises(ConnectorConfigError, match="GITHUB_INSTALLATION_ID"):
            GitHubConnectorConfig.from_properties(
                {"repository": "owner/repo", "auth_method": "app"}
            )

    def test_from_properties_github_app_invalid_app_id_raises_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Test from_properties raises error for invalid GITHUB_APP_ID."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        key_file = tmp_path / "private-key.pem"
        key_file.write_text("test key")

        monkeypatch.setenv("GITHUB_APP_ID", "not_a_number")
        monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", str(key_file))
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        with pytest.raises(ConnectorConfigError, match="Invalid GITHUB_APP_ID"):
            GitHubConnectorConfig.from_properties(
                {"repository": "owner/repo", "auth_method": "app"}
            )

    def test_from_properties_github_app_nonexistent_key_file_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties raises error when private key file doesn't exist."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_PRIVATE_KEY_PATH", "/nonexistent/path/key.pem")
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        with pytest.raises(ConnectorConfigError, match="private key file not found"):
            GitHubConnectorConfig.from_properties(
                {"repository": "owner/repo", "auth_method": "app"}
            )

    def test_from_properties_all_clone_strategies_valid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test from_properties accepts all valid clone strategies."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        strategies = ["minimal", "partial", "shallow", "full"]
        for strategy in strategies:
            config = GitHubConnectorConfig.from_properties(
                {"repository": "owner/repo", "clone_strategy": strategy}
            )
            assert config.clone_strategy == strategy

    def test_repository_whitespace_trimmed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that repository whitespace is trimmed."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        config = GitHubConnectorConfig.from_properties({"repository": "  owner/repo  "})

        assert config.repository == "owner/repo"

    def test_ref_empty_string_defaults_to_head(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that empty ref defaults to HEAD."""
        for var in GITHUB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        config = GitHubConnectorConfig.from_properties(
            {"repository": "owner/repo", "ref": ""}
        )

        assert config.ref == "HEAD"
