"""Tests for waivern_core.utils module."""

import pytest

from waivern_core.errors import ConnectorConfigError
from waivern_core.schemas import Schema
from waivern_core.utils import validate_output_schema


class TestValidateOutputSchema:
    """Tests for validate_output_schema() utility function."""

    def test_valid_schema_passes_without_raising(self) -> None:
        """Supported schema passes validation without raising an exception."""
        # Arrange
        schema = Schema("standard_input", "1.0.0")
        supported = [Schema("standard_input", "1.0.0"), Schema("findings", "1.0.0")]

        # Act & Assert - should not raise
        validate_output_schema(schema, supported)

    def test_unsupported_schema_raises_connector_config_error(self) -> None:
        """Unsupported schema raises ConnectorConfigError."""
        # Arrange
        schema = Schema("unsupported", "1.0.0")
        supported = [Schema("standard_input", "1.0.0")]

        # Act & Assert
        with pytest.raises(ConnectorConfigError):
            validate_output_schema(schema, supported)

    def test_error_message_includes_schema_name_and_version(self) -> None:
        """Error message includes the requested schema name and version."""
        # Arrange
        schema = Schema("unknown_schema", "2.5.0")
        supported = [Schema("standard_input", "1.0.0")]

        # Act & Assert
        with pytest.raises(ConnectorConfigError, match="unknown_schema"):
            validate_output_schema(schema, supported)

        with pytest.raises(ConnectorConfigError, match="2.5.0"):
            validate_output_schema(schema, supported)

    def test_error_message_lists_supported_schemas(self) -> None:
        """Error message lists all supported schemas."""
        # Arrange
        schema = Schema("unsupported", "1.0.0")
        supported = [Schema("standard_input", "1.0.0"), Schema("findings", "2.0.0")]

        # Act & Assert
        with pytest.raises(ConnectorConfigError, match="standard_input") as exc_info:
            validate_output_schema(schema, supported)

        error_message = str(exc_info.value)
        assert "standard_input" in error_message
        assert "findings" in error_message

    def test_comparison_uses_name_and_version(self) -> None:
        """Validation compares both name and version, not just name."""
        # Arrange - same name but different version
        schema = Schema("standard_input", "2.0.0")
        supported = [Schema("standard_input", "1.0.0")]

        # Act & Assert - should fail because version doesn't match
        with pytest.raises(ConnectorConfigError):
            validate_output_schema(schema, supported)
