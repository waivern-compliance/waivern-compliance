"""Configuration for MySQLConnector."""

import os
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator
from waivern_core.errors import ConnectorConfigError


class MySQLConnectorConfig(BaseModel):
    """Configuration for MySQLConnector with Pydantic validation.

    This provides strong typing and validation for MySQL connector
    configuration parameters with sensible defaults and environment variable support.
    """

    host: str = Field(description="MySQL server hostname")
    port: int = Field(
        default=3306,
        description="MySQL server port",
        gt=0,
        le=65535,
    )
    user: str = Field(description="Database username")
    password: str = Field(
        default="",
        description="Database password",
    )
    database: str = Field(
        default="",
        description="Database name to connect to",
    )
    charset: str = Field(
        default="utf8mb4",
        description="Character set for the connection",
    )
    autocommit: bool = Field(
        default=True,
        description="Enable autocommit mode",
    )
    connect_timeout: int = Field(
        default=10,
        description="Connection timeout in seconds",
        gt=0,
    )
    max_rows_per_table: int = Field(
        default=10,
        description="Maximum number of rows to extract per table",
        gt=0,
    )

    model_config = ConfigDict(
        # Allow extra fields for future extensibility
        extra="forbid",
        # Validate assignment to catch errors early
        validate_assignment=True,
    )

    @field_validator("host")
    @classmethod
    def validate_host_not_empty(cls, v: str) -> str:
        """Validate that host is not empty."""
        if not v.strip():
            raise ValueError("MySQL host is required")
        return v.strip()

    @field_validator("user")
    @classmethod
    def validate_user_not_empty(cls, v: str) -> str:
        """Validate that user is not empty."""
        if not v.strip():
            raise ValueError("MySQL user is required")
        return v.strip()

    @field_validator("password", mode="before")
    @classmethod
    def validate_password_handle_none(cls, v: str | None) -> str:
        """Convert None password to empty string."""
        if v is None:
            return ""
        return str(v)

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties with environment variable support.

        Environment variables take precedence over runbook properties:
        - MYSQL_HOST overrides host property
        - MYSQL_PORT overrides port property
        - MYSQL_USER overrides user property
        - MYSQL_PASSWORD overrides password property
        - MYSQL_DATABASE overrides database property

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Validated configuration object

        Raises:
            ConnectorConfigError: If validation fails or required properties are missing

        """
        try:
            # Merge environment variables with properties (env vars take precedence)
            config_data = properties.copy()

            # Required properties with env var fallback
            if "MYSQL_HOST" in os.environ:
                config_data["host"] = os.environ["MYSQL_HOST"]
            if "MYSQL_USER" in os.environ:
                config_data["user"] = os.environ["MYSQL_USER"]

            # Optional properties with env var fallback
            if "MYSQL_PASSWORD" in os.environ:
                config_data["password"] = os.environ["MYSQL_PASSWORD"]
            if "MYSQL_DATABASE" in os.environ:
                config_data["database"] = os.environ["MYSQL_DATABASE"]

            # Handle port with validation
            if "MYSQL_PORT" in os.environ:
                try:
                    config_data["port"] = int(os.environ["MYSQL_PORT"])
                except ValueError as e:
                    raise ConnectorConfigError(
                        f"Invalid MYSQL_PORT environment variable: {os.environ['MYSQL_PORT']}"
                    ) from e

            # Validate required fields are present (either from properties or env)
            if "host" not in config_data or config_data["host"] is None:
                raise ConnectorConfigError(
                    "MySQL host info is required (either 'host' property or MYSQL_HOST env var)"
                )
            if "user" not in config_data or config_data["user"] is None:
                raise ConnectorConfigError(
                    "MySQL user info is required (either 'user' property or MYSQL_USER env var)"
                )

            return cls.model_validate(config_data)
        except ValueError as e:
            # Convert Pydantic validation errors to ConnectorConfigError
            raise ConnectorConfigError(
                f"Invalid MySQL connector configuration: {e}"
            ) from e
