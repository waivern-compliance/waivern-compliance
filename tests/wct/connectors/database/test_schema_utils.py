"""Tests for database schema utility functions following TDD/BDD methodology."""

import pytest

from wct.connectors.base import ConnectorConfigError
from wct.connectors.database.schema_utils import DatabaseSchemaUtils
from wct.schemas import Schema, StandardInputSchema


class TestDatabaseSchemaUtils:
    """Test suite for DatabaseSchemaUtils following BDD patterns."""

    def test_validate_output_schema_accepts_supported_schema(self):
        """GIVEN a supported output schema
        WHEN validating the schema
        THEN it should return the schema unchanged"""
        # Arrange - Use different instances to test type-based matching
        schema = StandardInputSchema()
        different_instance = StandardInputSchema()
        supported_schemas = (different_instance,)

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
            def name(self) -> str:
                return "unsupported_schema"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def schema(self) -> dict:
                return {"type": "object"}

        unsupported_schema = UnsupportedTestSchema()
        supported_schemas = (StandardInputSchema(),)

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
        supported_schemas = (first_schema,)

        # Act
        result = DatabaseSchemaUtils.validate_output_schema(schema, supported_schemas)

        # Assert
        assert result is first_schema  # Should return the first supported schema
        assert result.name == "standard_input"
        assert result.version == "1.0.0"

    def test_validate_output_schema_rejects_duplicate_schema_types(self):
        """GIVEN supported schemas with duplicate types
        WHEN validating schema
        THEN it should raise ConnectorConfigError about duplicates"""
        # Arrange
        schema = StandardInputSchema()
        duplicate_schema = StandardInputSchema()
        supported_schemas = (schema, duplicate_schema)  # Same type - should be rejected

        # Act & Assert
        with pytest.raises(
            ConnectorConfigError, match="Duplicate schema types not allowed"
        ):
            DatabaseSchemaUtils.validate_output_schema(schema, supported_schemas)
