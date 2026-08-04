"""Configuration for GitHubConnector."""

import os
from pathlib import Path
from typing import Any, Literal, Self, override

from pydantic import Field, field_validator, model_validator
from waivern_core import BaseComponentConfiguration
from waivern_core.config_validation import validate_or_raise
from waivern_core.errors import ConnectorConfigError

# Type alias for clone strategy - single source of truth
CloneStrategy = Literal["minimal", "partial", "shallow", "full"]


class GitHubConnectorConfig(BaseComponentConfiguration):
    """Configuration for GitHubConnector with Pydantic validation.

    This provides strong typing and validation for GitHub connector
    configuration parameters with sensible defaults and environment variable support.
    """

    repository: str = Field(description="GitHub repository in 'owner/repo' format")
    ref: str = Field(
        default="HEAD",
        description="Git ref to checkout (branch, tag, or commit SHA)",
    )
    include_patterns: list[str] | None = Field(
        default=None,
        description="Glob patterns to include (positive filtering). Mutually exclusive with exclude_patterns.",
    )
    exclude_patterns: list[str] | None = Field(
        default=None,
        description="Glob patterns to exclude (negative filtering). Mutually exclusive with include_patterns.",
    )
    max_files: int = Field(
        default=1000,
        description="Maximum number of files to process",
        gt=0,
    )
    clone_strategy: CloneStrategy = Field(
        default="minimal",
        description="Clone strategy: minimal (fastest), partial, shallow, or full",
    )
    clone_timeout: int = Field(
        default=300,
        description="Clone timeout in seconds",
        gt=0,
    )
    auth_method: Literal["pat", "app"] = Field(
        default="pat",
        description="Authentication method: 'pat' (Personal Access Token) or 'app' (GitHub App)",
    )
    installation_id: str | None = Field(
        default=None,
        description=(
            "GitHub App installation ID. An opaque token owned by GitHub, so it is "
            "stored verbatim as a string rather than parsed. Varies per client, so "
            "it belongs in the runbook. The GITHUB_APP_INSTALLATION_ID environment "
            "variable overrides this value when set."
        ),
    )

    # Internal fields populated from environment variables.
    # app_id and private_key_path are the shared App identity + secret, so they
    # are env-only; installation_id is a public field above because it varies per
    # client and is supplied via the runbook.
    _token: str | None = None
    _app_id: int | None = None
    _private_key_path: Path | None = None

    @field_validator("repository")
    @classmethod
    def validate_repository_format(cls, v: str) -> str:
        """Validate repository is in 'owner/repo' format."""
        if not v or not v.strip():
            raise ValueError("repository is required")
        v = v.strip()
        if "/" not in v:
            raise ValueError("repository must be in 'owner/repo' format")
        parts = v.split("/")
        expected_parts = 2  # owner/repo format has exactly 2 parts
        if len(parts) != expected_parts or not parts[0] or not parts[1]:
            raise ValueError("repository must be in 'owner/repo' format")
        return v

    @field_validator("ref")
    @classmethod
    def validate_ref_not_empty(cls, v: str) -> str:
        """Validate ref is not empty."""
        if not v or not v.strip():
            return "HEAD"
        return v.strip()

    @model_validator(mode="after")
    def validate_patterns_mutual_exclusivity(self) -> Self:
        """Validate that include_patterns and exclude_patterns are mutually exclusive."""
        if self.include_patterns and self.exclude_patterns:
            raise ValueError(
                "include_patterns and exclude_patterns are mutually exclusive"
            )
        return self

    @property
    def token(self) -> str | None:
        """Get the authentication token."""
        return self._token

    @property
    def app_id(self) -> int | None:
        """Get the GitHub App ID."""
        return self._app_id

    @property
    def private_key_path(self) -> Path | None:
        """Get the path to the GitHub App private key."""
        return self._private_key_path

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties with environment variable support.

        Environment variables for PAT authentication:
        - GITHUB_TOKEN: Personal Access Token

        Environment variables for GitHub App authentication:
        - GITHUB_APP_ID: GitHub App ID
        - GITHUB_APP_PRIVATE_KEY_PATH: Path to private key .pem file
        - GITHUB_APP_INSTALLATION_ID: Installation ID

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Validated configuration object

        Raises:
            ConnectorConfigError: If validation fails or required properties are missing

        """
        config_data = properties.copy()

        # Validate required repository field
        if "repository" not in config_data or not config_data["repository"]:
            raise ConnectorConfigError("repository property is required")

        # Create the config instance first
        config = validate_or_raise(cls, config_data, ConnectorConfigError)

        # Handle authentication based on auth_method
        match config.auth_method:
            case "pat":
                token = os.environ.get("GITHUB_TOKEN")
                if token:
                    object.__setattr__(config, "_token", token)
                # Token is optional for public repos

            case "app":
                # app_id and private_key_path are the shared App identity + secret,
                # sourced only from the environment.
                app_id_str = os.environ.get("GITHUB_APP_ID")
                private_key_path_str = os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH")

                if not app_id_str:
                    raise ConnectorConfigError(
                        "GITHUB_APP_ID environment variable is required for GitHub App authentication"
                    )
                if not private_key_path_str:
                    raise ConnectorConfigError(
                        "GITHUB_APP_PRIVATE_KEY_PATH environment variable is required for GitHub App authentication"
                    )

                try:
                    app_id = int(app_id_str)
                except ValueError as e:
                    raise ConnectorConfigError(
                        f"Invalid GITHUB_APP_ID: must be an integer, got '{app_id_str}'"
                    ) from e

                private_key_path = Path(private_key_path_str)
                if not private_key_path.exists():
                    raise ConnectorConfigError(
                        f"GitHub App private key file not found: {private_key_path}"
                    )

                object.__setattr__(config, "_app_id", app_id)
                object.__setattr__(config, "_private_key_path", private_key_path)

                # installation_id varies per client: the runbook property supplies
                # it and GITHUB_APP_INSTALLATION_ID overrides when set. Exactly one
                # source is required. It is an opaque GitHub token, so the env value
                # is used verbatim without parsing.
                installation_id_env = os.environ.get("GITHUB_APP_INSTALLATION_ID")
                if installation_id_env:
                    object.__setattr__(config, "installation_id", installation_id_env)

                if config.installation_id is None:
                    raise ConnectorConfigError(
                        "installation_id is required for GitHub App authentication: "
                        "set it in the runbook source properties or the "
                        "GITHUB_APP_INSTALLATION_ID environment variable"
                    )

        return config
