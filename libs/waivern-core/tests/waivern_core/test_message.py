"""Tests for Message class with typed schemas."""

from dataclasses import dataclass, field
from typing import Any, override

import pytest

from waivern_core.message import Message, MessageValidationError, Schema


@dataclass(frozen=True, slots=True)
class MockTypedSchema(Schema):
    """Mock schema for testing Message integration with typed schemas."""

    _name: str = "test_schema"
    _version: str = "1.0.0"
    _schema_definition: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {"test": {"type": "string"}},
            "required": ["test"],
        }
    )

    @property
    @override
    def name(self) -> str:
        return self._name

    @property
    @override
    def version(self) -> str:
        return self._version

    @property
    @override
    def schema(self) -> dict[str, Any]:
        return self._schema_definition


class TestMessage:
    """Tests for Message class with typed schemas."""

    def test_create_message_with_typed_schema(self) -> None:
        """Test creating a message with a typed schema."""
        schema = MockTypedSchema()
        message = Message(id="test-id", content={"test": "value"}, schema=schema)

        assert message.id == "test-id"
        assert message.content == {"test": "value"}
        assert message.schema == schema
        assert message.schema_validated is False

    def test_validate_message_success(self) -> None:
        """Test successful message validation with typed schema."""
        schema = MockTypedSchema()
        message = Message(id="test-id", content={"test": "value"}, schema=schema)

        result = message.validate()

        assert result == message  # Should return self for chaining
        assert message.schema_validated is True

    def test_validate_message_invalid_content(self) -> None:
        """Test validation failure with invalid content."""
        schema = MockTypedSchema()
        message = Message(
            id="test-id",
            content={"invalid": "content"},  # Missing required "test" field
            schema=schema,
        )

        with pytest.raises(MessageValidationError) as exc_info:
            message.validate()

        assert "Schema validation failed" in str(exc_info.value)
        assert message.schema_validated is False

    def test_validate_message_no_content(self) -> None:
        """Test validation failure when no content provided."""
        schema = MockTypedSchema()
        message = Message(id="test-id", content={}, schema=schema)

        with pytest.raises(MessageValidationError) as exc_info:
            message.validate()

        assert "No content provided for validation" in str(exc_info.value)
        assert message.schema_validated is False

    def test_message_with_context(self) -> None:
        """Test message creation with context."""
        schema = MockTypedSchema()
        context = {"user_id": "123", "timestamp": "2025-01-01"}

        message = Message(
            id="test-id", content={"test": "value"}, schema=schema, context=context
        )

        assert message.context == context

    def test_message_validation_chaining(self) -> None:
        """Test that validation can be chained."""
        schema = MockTypedSchema()
        message = Message(id="test-id", content={"test": "value"}, schema=schema)

        # Should be able to chain validation
        result = message.validate()
        assert result is message
        assert message.schema_validated is True
