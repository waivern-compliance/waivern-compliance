"""Tests for base database connector functionality."""

from typing import Any, Self, override

import pytest
from waivern_community.connectors.source_code.schemas import SourceCodeSchema
from waivern_core.base_connector import Connector
from waivern_core.message import Message
from waivern_core.schemas.base import Schema

from waivern_connectors_database import DatabaseConnector


class TestBaseDatabaseConnector:
    """Test shared database connector functionality."""

    def test_base_connector_supports_standard_input_schema(self) -> None:
        """Test that all database connectors support standard_input schema."""
        # Act
        supported_schemas = DatabaseConnector.get_supported_output_schemas()

        # Assert
        assert len(supported_schemas) == 1
        assert supported_schemas[0].name == "standard_input"
        assert supported_schemas[0].version == "1.0.0"

    def test_base_connector_is_abstract_class(self) -> None:
        """Test that DatabaseConnector cannot be instantiated directly as it's abstract."""
        # Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DatabaseConnector()  # type: ignore

    def test_base_connector_subclass_can_override_supported_schemas(self) -> None:
        """Test that DatabaseConnector subclasses can override supported output schemas."""

        # Arrange
        class TestDatabaseConnector(DatabaseConnector):
            @classmethod
            @override
            def get_name(cls) -> str:
                return "test_db"

            @classmethod
            @override
            def from_properties(cls, properties: dict[str, Any]) -> Self:
                return cls()

            @classmethod
            @override
            def get_supported_output_schemas(cls) -> list[Schema]:
                return [SourceCodeSchema()]  # Override to support different schema

            @override
            def extract(self, output_schema: Schema) -> Message:
                return Message(id="test", content={}, schema=output_schema)

        # Act
        supported_schemas = TestDatabaseConnector.get_supported_output_schemas()

        # Assert
        assert len(supported_schemas) == 1
        assert supported_schemas[0].name == "source_code"

    def test_base_connector_inherits_from_connector_interface(self) -> None:
        """Test that DatabaseConnector properly inherits from base Connector class."""
        # Arrange & Act - Assert
        assert issubclass(DatabaseConnector, Connector)
        assert hasattr(DatabaseConnector, "get_name")
        assert hasattr(DatabaseConnector, "from_properties")
        assert hasattr(DatabaseConnector, "get_supported_output_schemas")
        assert hasattr(DatabaseConnector, "extract")
