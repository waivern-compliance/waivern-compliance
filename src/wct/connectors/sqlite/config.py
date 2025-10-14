"""Configuration for SQLiteConnector."""

import os
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from waivern_core.errors import ConnectorConfigError


class SQLiteConnectorConfig(BaseModel):
    """Configuration for SQLiteConnector with Pydantic validation.

    This provides strong typing and validation for SQLite connector
    configuration parameters with sensible defaults and environment variable support.
    """

    database_path: str = Field(description="Path to SQLite database file")
    max_rows_per_table: int = Field(
        default=10,
        description="Maximum number of rows to extract per table",
        gt=0,
    )

    model_config = ConfigDict(
        # Forbid extra fields for strict validation
        extra="forbid",
        # Validate assignment to catch errors early
        validate_assignment=True,
    )

    @field_validator("database_path", mode="before")
    @classmethod
    def validate_database_path_not_empty(cls, v: str | None) -> str:
        """Validate that database_path is not empty."""
        if v is None or not str(v).strip():
            raise ValueError("database_path is required")
        return str(v).strip()

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties with environment variable support.

        Environment variables take precedence over runbook properties:
        - SQLITE_DATABASE_PATH overrides database_path property

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Validated configuration object

        Raises:
            ConnectorConfigError: If validation fails or required properties are missing

        """
        try:
            # Environment variables take precedence
            database_path = os.getenv(
                "SQLITE_DATABASE_PATH", properties.get("database_path", "")
            )
            max_rows_per_table = int(properties.get("max_rows_per_table", 10))

            return cls(
                database_path=database_path,
                max_rows_per_table=max_rows_per_table,
            )

        except (ValueError, TypeError, ValidationError) as e:
            raise ConnectorConfigError(f"SQLite configuration error: {e}") from e
