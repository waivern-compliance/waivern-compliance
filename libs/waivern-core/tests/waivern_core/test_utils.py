"""Tests for waivern_core.utils module."""

from datetime import datetime

import pytest

from waivern_core.errors import ConnectorConfigError
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_core.utils import update_analyses_chain, validate_output_schema


class TestUpdateAnalysesChain:
    """Tests for update_analyses_chain() utility function."""

    def test_creates_first_entry_with_order_one(self) -> None:
        """First analyser in chain gets order=1."""
        # Arrange
        message = Message(
            id="test",
            content={"data": "test"},
            schema=Schema("standard_input", "1.0.0"),
        )

        # Act
        result = update_analyses_chain(message, "test_analyser")

        # Assert
        assert len(result) == 1
        assert result[0]["order"] == 1
        assert result[0]["analyser"] == "test_analyser"

    def test_increments_order_for_subsequent_entries(self) -> None:
        """Subsequent analysers get incremented order numbers."""
        # Arrange
        message = Message(
            id="test",
            content={
                "data": "test",
                "analysis_metadata": {
                    "analyses_chain": [
                        {"order": 1, "analyser": "first_analyser"},
                        {"order": 2, "analyser": "second_analyser"},
                    ]
                },
            },
            schema=Schema("standard_input", "1.0.0"),
        )

        # Act
        result = update_analyses_chain(message, "third_analyser")

        # Assert
        assert len(result) == 3
        assert result[-1]["order"] == 3
        assert result[-1]["analyser"] == "third_analyser"

    def test_preserves_existing_chain_entries(self) -> None:
        """Existing chain entries are preserved in returned list."""
        # Arrange
        existing_entries = [
            {"order": 1, "analyser": "first_analyser"},
            {"order": 2, "analyser": "second_analyser"},
        ]
        message = Message(
            id="test",
            content={"analysis_metadata": {"analyses_chain": existing_entries}},
            schema=Schema("standard_input", "1.0.0"),
        )

        # Act
        result = update_analyses_chain(message, "new_analyser")

        # Assert - existing entries are preserved unchanged
        assert result[0] == existing_entries[0]
        assert result[1] == existing_entries[1]

    def test_adds_execution_timestamp(self) -> None:
        """New entry includes execution_timestamp."""
        # Arrange
        message = Message(
            id="test",
            content={"data": "test"},
            schema=Schema("standard_input", "1.0.0"),
        )

        # Act
        result = update_analyses_chain(message, "test_analyser")

        # Assert
        assert "execution_timestamp" in result[0]
        assert isinstance(result[0]["execution_timestamp"], datetime)


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
