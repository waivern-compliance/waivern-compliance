"""Configuration for MongoDBConnector."""

import os
from typing import Any, Self, override

from pydantic import Field, field_validator
from waivern_core import BaseComponentConfiguration
from waivern_core.errors import ConnectorConfigError


class MongoDBConnectorConfig(BaseComponentConfiguration):
    """Configuration for MongoDBConnector with Pydantic validation.

    This provides strong typing and validation for MongoDB connector
    configuration parameters with sensible defaults and environment variable support.
    """

    uri: str = Field(description="MongoDB connection URI")
    database: str = Field(description="Database name to connect to")
    sample_size: int = Field(
        default=10,
        description="Maximum number of documents to sample per collection",
        gt=0,
    )

    @field_validator("uri")
    @classmethod
    def validate_uri_not_empty(cls, v: str) -> str:
        """Validate that uri is not empty."""
        if not v.strip():
            raise ValueError("MongoDB uri is required")
        return v.strip()

    @field_validator("database")
    @classmethod
    def validate_database_not_empty(cls, v: str) -> str:
        """Validate that database is not empty."""
        if not v.strip():
            raise ValueError("MongoDB database is required")
        return v.strip()

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties with environment variable support.

        Environment variables take precedence over runbook properties:
        - MONGODB_URI overrides uri property
        - MONGODB_DATABASE overrides database property

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

            # Environment variable overrides
            if "MONGODB_URI" in os.environ:
                config_data["uri"] = os.environ["MONGODB_URI"]
            if "MONGODB_DATABASE" in os.environ:
                config_data["database"] = os.environ["MONGODB_DATABASE"]

            # Validate required fields are present (either from properties or env)
            if "uri" not in config_data or config_data["uri"] is None:
                raise ConnectorConfigError(
                    "MongoDB uri is required (either 'uri' property or MONGODB_URI env var)"
                )
            if "database" not in config_data or config_data["database"] is None:
                raise ConnectorConfigError(
                    "MongoDB database is required "
                    "(either 'database' property or MONGODB_DATABASE env var)"
                )

            return cls.model_validate(config_data)
        except ValueError as e:
            # Convert Pydantic validation errors to ConnectorConfigError
            raise ConnectorConfigError(
                f"Invalid MongoDB connector configuration: {e}"
            ) from e
