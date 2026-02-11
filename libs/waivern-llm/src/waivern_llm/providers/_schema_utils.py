"""Internal schema utilities for LLM providers.

This module contains shared utilities for transforming JSON schemas to meet
provider-specific requirements (e.g., strict mode constraints).
"""

from typing import Any


def ensure_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Add ``additionalProperties: false`` to all objects in a JSON schema.

    Both OpenAI and Anthropic's structured-output modes require every object
    definition to include ``"additionalProperties": false``. Pydantic's
    ``model_json_schema()`` does not emit this by default.

    Operates recursively on the schema, including ``$defs`` and nested objects.
    Returns a new dict — the original is not mutated.

    Args:
        schema: JSON schema dictionary to transform.

    Returns:
        New schema dictionary with ``additionalProperties: false`` added to
        all object definitions.

    """
    schema = dict(schema)

    if schema.get("type") == "object":
        schema["additionalProperties"] = False

    # Recurse into properties
    if "properties" in schema:
        schema["properties"] = {
            key: ensure_strict_schema(value)  # type: ignore[arg-type]
            for key, value in schema["properties"].items()  # type: ignore[union-attr]
        }

    # Recurse into $defs (Pydantic puts referenced models here)
    if "$defs" in schema:
        schema["$defs"] = {
            key: ensure_strict_schema(value)  # type: ignore[arg-type]
            for key, value in schema["$defs"].items()  # type: ignore[union-attr]
        }

    # Recurse into array items
    if "items" in schema and isinstance(schema["items"], dict):
        schema["items"] = ensure_strict_schema(schema["items"])  # type: ignore[arg-type]

    return schema
