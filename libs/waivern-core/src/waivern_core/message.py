"""Message handling for Waivern Compliance Framework components.

This module provides:
- Message: universal communication unit between framework components
- MessageExtensions: optional typed metadata (execution, tracing, etc.)
- ExecutionContext: execution-specific metadata filled by executor
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Self

import jsonschema

from waivern_core.errors import MessageValidationError
from waivern_core.schemas import Schema, SchemaLoadError


@dataclass(slots=True)
class ExecutionContext:
    """Execution-specific metadata, populated by executor after component runs.

    This context captures the outcome of executing a component (connector/processor)
    and is used for tracking, streaming to WCT, and observability.
    """

    status: Literal["pending", "success", "error"]
    """Execution status."""

    error: str | None = None
    """Error message if status is 'error'."""

    duration_seconds: float | None = None
    """Time taken to execute the component."""

    origin: str = "parent"
    """Origin of the message: 'parent' or 'child:{runbook_name}'."""

    alias: str | None = None
    """Parent artifact name if this is from a child runbook."""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to dictionary."""
        return {
            "status": self.status,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "origin": self.origin,
            "alias": self.alias,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Reconstruct from dictionary."""
        return cls(
            status=data["status"],
            error=data.get("error"),
            duration_seconds=data.get("duration_seconds"),
            origin=data.get("origin", "parent"),
            alias=data.get("alias"),
        )


@dataclass(slots=True)
class MessageExtensions:
    """Optional typed metadata for messages.

    Provides an extensible way to attach additional context without
    polluting the core Message fields. New extension types can be
    added as needs arise (tracing, billing, streaming, etc.).
    """

    execution: ExecutionContext | None = None
    """Execution context, populated by executor."""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to dictionary."""
        return {
            "execution": self.execution.to_dict() if self.execution else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Reconstruct from dictionary."""
        execution_data = data.get("execution")
        return cls(
            execution=ExecutionContext.from_dict(execution_data)
            if execution_data
            else None,
        )


@dataclass(slots=True)
class Message:
    """Universal communication unit between WCF components.

    Message serves as the delivery mechanism for all inter-component
    communication in WCF - from connectors to processors, processors
    to downstream processors, and processors to the executor.

    Structure follows CloudEvents-inspired pattern:
    - Identity: id, run_id
    - Routing: source, timestamp
    - Contract: schema
    - Payload: content, context
    - Extensions: optional typed metadata
    """

    # === Identity ===
    id: str
    """Unique identifier for this message."""

    # === Payload ===
    content: dict[str, Any]
    """The actual data payload, conforming to schema."""

    # === Contract ===
    schema: Schema
    """Schema defining the structure of content."""

    # === Optional fields (populated by executor or component) ===
    context: dict[str, Any] | None = None
    """Optional context metadata (user info, timestamps, etc.)."""

    run_id: str | None = None
    """Run identifier for correlation. Set by executor."""

    source: str | None = None
    """Component that produced this message (e.g., 'connector:filesystem')."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    """When the message was created."""

    extensions: MessageExtensions | None = None
    """Optional typed metadata (execution, tracing, etc.)."""

    # === Execution Context Convenience Properties ===

    @property
    def is_success(self) -> bool:
        """Check if execution succeeded.

        Returns False if no execution context is present.
        """
        if self.extensions and self.extensions.execution:
            return self.extensions.execution.status == "success"
        return False

    @property
    def execution_error(self) -> str | None:
        """Get execution error message, if any."""
        if self.extensions and self.extensions.execution:
            return self.extensions.execution.error
        return None

    @property
    def execution_duration(self) -> float | None:
        """Get execution duration in seconds, if available."""
        if self.extensions and self.extensions.execution:
            return self.extensions.execution.duration_seconds
        return None

    @property
    def execution_origin(self) -> str | None:
        """Get execution origin (e.g., 'parent' or 'child:name')."""
        if self.extensions and self.extensions.execution:
            return self.extensions.execution.origin
        return None

    @property
    def execution_alias(self) -> str | None:
        """Get execution alias for child runbook artifacts."""
        if self.extensions and self.extensions.execution:
            return self.extensions.execution.alias
        return None

    # === Validation ===

    def validate(self) -> Self:
        """Validate the message content against its schema.

        Validates on-demand - no cached state. Call this explicitly when
        validation is required (e.g., at system boundaries).

        Returns:
            Self for method chaining

        Raises:
            MessageValidationError: If validation fails

        """
        if not self.content:
            raise MessageValidationError("No content provided for validation")

        try:
            schema_definition = self.schema.schema
            jsonschema.validate(self.content, schema_definition)
            return self

        except jsonschema.ValidationError as e:
            raise MessageValidationError(
                f"Schema validation failed for schema '{self.schema.name}': {e.message}"
            ) from e
        except (FileNotFoundError, SchemaLoadError) as e:
            raise MessageValidationError(
                f"Schema loading failed for '{self.schema.name}': {e}"
            ) from e
        except Exception as e:
            raise MessageValidationError(f"Validation error: {e}") from e

    def to_dict(self) -> dict[str, Any]:
        """Serialise message to dictionary for transport/storage.

        Returns:
            JSON-serialisable dictionary representation.

        """
        return {
            "id": self.id,
            "content": self.content,
            "schema": self.schema.__getstate__(),
            "context": self.context,
            "run_id": self.run_id,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "extensions": self.extensions.to_dict() if self.extensions else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Reconstruct message from dictionary.

        Args:
            data: Dictionary from to_dict().

        Returns:
            Reconstructed Message instance.

        """
        schema = Schema.__new__(Schema)
        schema.__setstate__(data["schema"])

        extensions_data = data.get("extensions")
        extensions = (
            MessageExtensions.from_dict(extensions_data) if extensions_data else None
        )

        timestamp_str = data.get("timestamp")
        timestamp = (
            datetime.fromisoformat(timestamp_str)
            if timestamp_str
            else datetime.now(UTC)
        )

        return cls(
            id=data["id"],
            content=data["content"],
            schema=schema,
            context=data.get("context"),
            run_id=data.get("run_id"),
            source=data.get("source"),
            timestamp=timestamp,
            extensions=extensions,
        )
