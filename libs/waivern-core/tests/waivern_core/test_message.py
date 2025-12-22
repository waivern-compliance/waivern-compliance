"""Tests for Message class with typed schemas."""

from dataclasses import dataclass, field
from typing import Any, override

import pytest

from waivern_core.message import (
    ExecutionContext,
    Message,
    MessageExtensions,
    MessageValidationError,
    Schema,
)


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


# =============================================================================
# Core Message Tests - Creation and Validation
# =============================================================================


class TestMessage:
    """Tests for Message class with typed schemas."""

    def test_create_message_with_typed_schema(self) -> None:
        """Test creating a message with a typed schema."""
        schema = MockTypedSchema()
        message = Message(id="test-id", content={"test": "value"}, schema=schema)

        assert message.id == "test-id"
        assert message.content == {"test": "value"}
        assert message.schema == schema

    def test_validate_message_success(self) -> None:
        """Test successful message validation with typed schema."""
        schema = MockTypedSchema()
        message = Message(id="test-id", content={"test": "value"}, schema=schema)

        result = message.validate()

        assert result is message  # Returns self for chaining

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

    def test_validate_message_no_content(self) -> None:
        """Test validation failure when no content provided."""
        schema = MockTypedSchema()
        message = Message(id="test-id", content={}, schema=schema)

        with pytest.raises(MessageValidationError) as exc_info:
            message.validate()

        assert "No content provided for validation" in str(exc_info.value)

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


# =============================================================================
# Execution Context Convenience Properties
# =============================================================================


class TestMessageExecutionProperties:
    """Tests for Message convenience properties that access ExecutionContext."""

    def test_is_success_returns_true_for_success_status(self) -> None:
        """is_success returns True when execution status is 'success'."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(execution=ExecutionContext(status="success")),
        )

        assert message.is_success is True

    def test_is_success_returns_false_for_error_status(self) -> None:
        """is_success returns False when execution status is 'error'."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(
                execution=ExecutionContext(status="error", error="Something failed")
            ),
        )

        assert message.is_success is False

    def test_is_success_returns_false_for_pending_status(self) -> None:
        """is_success returns False when execution status is 'pending'."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(execution=ExecutionContext(status="pending")),
        )

        assert message.is_success is False

    def test_is_success_returns_false_without_extensions(self) -> None:
        """is_success returns False when no extensions present."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
        )

        assert message.is_success is False

    def test_is_success_returns_false_without_execution(self) -> None:
        """is_success returns False when extensions exist but no execution."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(execution=None),
        )

        assert message.is_success is False

    def test_execution_error_returns_error_message(self) -> None:
        """execution_error returns the error message when present."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(
                execution=ExecutionContext(status="error", error="Connection timeout")
            ),
        )

        assert message.execution_error == "Connection timeout"

    def test_execution_error_returns_none_for_success(self) -> None:
        """execution_error returns None for successful execution."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(execution=ExecutionContext(status="success")),
        )

        assert message.execution_error is None

    def test_execution_error_returns_none_without_extensions(self) -> None:
        """execution_error returns None when no extensions present."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
        )

        assert message.execution_error is None

    def test_execution_duration_returns_duration_seconds(self) -> None:
        """execution_duration returns the duration in seconds."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(
                execution=ExecutionContext(status="success", duration_seconds=1.234)
            ),
        )

        assert message.execution_duration == 1.234

    def test_execution_duration_returns_none_when_not_set(self) -> None:
        """execution_duration returns None when duration not recorded."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(execution=ExecutionContext(status="success")),
        )

        assert message.execution_duration is None

    def test_execution_duration_returns_none_without_extensions(self) -> None:
        """execution_duration returns None when no extensions present."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
        )

        assert message.execution_duration is None

    def test_execution_origin_returns_parent(self) -> None:
        """execution_origin returns 'parent' for parent artifacts."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(
                execution=ExecutionContext(status="success", origin="parent")
            ),
        )

        assert message.execution_origin == "parent"

    def test_execution_origin_returns_child_name(self) -> None:
        """execution_origin returns 'child:name' for child runbook artifacts."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(
                execution=ExecutionContext(
                    status="success", origin="child:personal_data_analyser"
                )
            ),
        )

        assert message.execution_origin == "child:personal_data_analyser"

    def test_execution_origin_returns_none_without_extensions(self) -> None:
        """execution_origin returns None when no extensions present."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
        )

        assert message.execution_origin is None

    def test_execution_alias_returns_alias(self) -> None:
        """execution_alias returns the alias for child runbook artifacts."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(
                execution=ExecutionContext(
                    status="success",
                    origin="child:analyser",
                    alias="findings",
                )
            ),
        )

        assert message.execution_alias == "findings"

    def test_execution_alias_returns_none_for_parent(self) -> None:
        """execution_alias returns None for parent artifacts."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(
                execution=ExecutionContext(status="success", origin="parent")
            ),
        )

        assert message.execution_alias is None

    def test_execution_alias_returns_none_without_extensions(self) -> None:
        """execution_alias returns None when no extensions present."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
        )

        assert message.execution_alias is None


# =============================================================================
# Serialisation - to_dict and from_dict
# =============================================================================


class TestMessageSerialization:
    """Tests for Message serialization with extensions."""

    def test_to_dict_includes_extensions(self) -> None:
        """to_dict includes extensions when present."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
            extensions=MessageExtensions(
                execution=ExecutionContext(
                    status="success",
                    duration_seconds=1.5,
                    origin="parent",
                )
            ),
        )

        result = message.to_dict()

        assert result["extensions"] is not None
        assert result["extensions"]["execution"]["status"] == "success"
        assert result["extensions"]["execution"]["duration_seconds"] == 1.5
        assert result["extensions"]["execution"]["origin"] == "parent"

    def test_to_dict_extensions_none_when_not_set(self) -> None:
        """to_dict has extensions=None when not set."""
        message = Message(
            id="test-id",
            content={"test": "value"},
            schema=MockTypedSchema(),
        )

        result = message.to_dict()

        assert result["extensions"] is None

    def test_from_dict_reconstructs_extensions(self) -> None:
        """from_dict correctly reconstructs extensions."""
        data = {
            "id": "test-id",
            "content": {"test": "value"},
            "schema": {"name": "test_schema", "version": "1.0.0"},
            "context": None,
            "run_id": None,
            "source": None,
            "timestamp": "2025-01-01T12:00:00+00:00",
            "extensions": {
                "execution": {
                    "status": "error",
                    "error": "Connection failed",
                    "duration_seconds": 0.5,
                    "origin": "child:analyser",
                    "alias": "results",
                }
            },
        }

        message = Message.from_dict(data)

        assert message.is_success is False
        assert message.execution_error == "Connection failed"
        assert message.execution_duration == 0.5
        assert message.execution_origin == "child:analyser"
        assert message.execution_alias == "results"

    def test_from_dict_handles_no_extensions(self) -> None:
        """from_dict handles missing extensions gracefully."""
        data = {
            "id": "test-id",
            "content": {"test": "value"},
            "schema": {"name": "test_schema", "version": "1.0.0"},
            "context": None,
            "run_id": None,
            "source": None,
            "timestamp": "2025-01-01T12:00:00+00:00",
            "extensions": None,
        }

        message = Message.from_dict(data)

        assert message.extensions is None
        assert message.is_success is False
        assert message.execution_error is None

    def test_round_trip_preserves_extensions(self) -> None:
        """Round-trip through to_dict/from_dict preserves all extension data."""
        # Use base Schema for round-trip test (MockTypedSchema is a frozen
        # dataclass with different serialization)
        original = Message(
            id="test-id",
            content={"test": "value"},
            schema=Schema("test_schema", "1.0.0"),
            run_id="run-123",
            source="connector:filesystem",
            extensions=MessageExtensions(
                execution=ExecutionContext(
                    status="success",
                    error=None,
                    duration_seconds=2.5,
                    origin="child:processor",
                    alias="output",
                )
            ),
        )

        # Round-trip
        data = original.to_dict()
        restored = Message.from_dict(data)

        # Verify all extension data is preserved
        assert restored.is_success == original.is_success
        assert restored.execution_error == original.execution_error
        assert restored.execution_duration == original.execution_duration
        assert restored.execution_origin == original.execution_origin
        assert restored.execution_alias == original.execution_alias

        # Verify other fields preserved too
        assert restored.id == original.id
        assert restored.content == original.content
        assert restored.run_id == original.run_id
        assert restored.source == original.source
