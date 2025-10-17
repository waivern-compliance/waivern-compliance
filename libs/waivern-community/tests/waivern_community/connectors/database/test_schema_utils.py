"""Tests for database schema utility functions following TDD/BDD methodology."""

from typing import override

import pytest
from waivern_core.errors import ConnectorConfigError
from waivern_core.schemas import StandardInputSchema
from waivern_core.schemas.base import Schema

from waivern_community.connectors.database.schema_utils import DatabaseSchemaUtils


class TestDatabaseSchemaUtils:
    """Test suite for DatabaseSchemaUtils following BDD patterns."""

    def test_validate_output_schema_accepts_supported_schema(self):
        """GIVEN a supported output schema
        WHEN validating the schema
        THEN it should return the schema unchanged"""
        # Arrange - Use different instances to test type-based matching
        schema = StandardInputSchema()
        different_instance = StandardInputSchema()
        supported_schemas: list[Schema] = [different_instance]

        # Act
        result = DatabaseSchemaUtils.validate_output_schema(schema, supported_schemas)

        # Assert
        assert result == schema
        assert result.name == "standard_input"
        assert result.version == "1.0.0"
        # Verify we got back the original schema, not the supported one
        assert result is schema

    def test_validate_output_schema_rejects_unsupported_schema(self):
        """GIVEN an unsupported output schema
        WHEN validating the schema
        THEN it should raise ConnectorConfigError with descriptive message"""

        # Arrange
        # Create a proper unsupported schema for testing
        class UnsupportedTestSchema(Schema):
            @property
            @override
            def name(self) -> str:
                return "unsupported_schema"

            @property
            @override
            def version(self) -> str:
                return "1.0.0"

            @property
            @override
            def schema(self) -> dict[str, str]:
                return {"type": "object"}

        unsupported_schema = UnsupportedTestSchema()
        supported_schemas: list[Schema] = [StandardInputSchema()]

        # Act & Assert
        with pytest.raises(
            ConnectorConfigError, match="Unsupported output schema: unsupported_schema"
        ):
            DatabaseSchemaUtils.validate_output_schema(
                unsupported_schema, supported_schemas
            )

    def test_validate_output_schema_uses_default_when_none(self):
        """GIVEN no schema provided (None)
        WHEN validating the schema
        THEN it should return the first supported schema as default"""
        # Arrange
        schema = None
        first_schema = StandardInputSchema()
        supported_schemas: list[Schema] = [first_schema]

        # Act
        result = DatabaseSchemaUtils.validate_output_schema(schema, supported_schemas)

        # Assert
        assert result is first_schema  # Should return the first supported schema
        assert result.name == "standard_input"
        assert result.version == "1.0.0"

    def test_validate_output_schema_handles_duplicate_schema_types(self):
        """GIVEN supported schemas with duplicate types
        WHEN validating schema
        THEN it should automatically deduplicate and work correctly"""
        # Arrange
        schema = StandardInputSchema()
        duplicate_schema = StandardInputSchema()
        supported_schemas: list[Schema] = [
            schema,
            duplicate_schema,
        ]  # Same type - should be deduplicated

        # Act
        result = DatabaseSchemaUtils.validate_output_schema(schema, supported_schemas)

        # Assert - should work fine and return the original schema
        assert result == schema
        assert result.name == "standard_input"
        assert result.version == "1.0.0"
