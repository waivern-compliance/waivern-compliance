"""Shared fixtures for waivern-core tests."""

from dataclasses import dataclass, field
from typing import Any, override

from waivern_core.schemas import Schema

# =============================================================================
# Mock Schema Classes
# =============================================================================


@dataclass(frozen=True, slots=True)
class MockTypedSchema(Schema):
    """Mock schema for testing Message integration with typed schemas.

    This is a minimal typed schema implementation for tests that need a schema
    with a custom schema definition. For simple schema needs, use the base
    Schema class directly.
    """

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
