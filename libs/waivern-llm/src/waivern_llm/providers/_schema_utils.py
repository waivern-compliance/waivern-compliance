"""Internal schema utilities for LLM providers.

This module contains shared utilities for transforming JSON schemas to meet
provider-specific requirements (e.g., strict mode constraints).
"""

from typing import Any

# Fields that Gemini's response_schema does not use and should be stripped.
_GEMINI_STRIP_FIELDS = frozenset({"title", "default"})


def convert_to_gemini_schema(
    schema: dict[str, Any],
    _defs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert a standard JSON Schema into Gemini's ``response_schema`` format.

    Gemini's file-based batch API uses an OpenAPI 3.0-style schema dialect
    that differs from standard JSON Schema in several ways:

    1. Type names must be capitalised (``STRING``, ``OBJECT``, ``ARRAY``, etc.)
    2. ``$ref`` / ``$defs`` are not supported — references must be inlined
    3. ``title`` and ``default`` are stripped (unsupported metadata)

    Operates recursively.  Returns a new dict — the original is not mutated.

    Args:
        schema: JSON schema dictionary (e.g., from ``model_json_schema()``).
        _defs: Internal — resolved definitions dict passed during recursion.

    Returns:
        New schema dictionary in Gemini's expected format.

    """
    # On the first (non-recursive) call, capture $defs for later resolution.
    if _defs is None:
        _defs = schema.get("$defs", {})
        return convert_to_gemini_schema(schema, _defs)

    result: dict[str, Any] = {}

    for key, value in schema.items():
        # Strip unsupported metadata fields.
        if key in _GEMINI_STRIP_FIELDS:
            continue

        # Strip $defs — definitions are inlined at each $ref site.
        if key == "$defs":
            continue

        match key:
            case "type":
                result["type"] = value.upper() if isinstance(value, str) else value
            case "properties":
                result["properties"] = {
                    prop_name: convert_to_gemini_schema(prop_schema, _defs)
                    for prop_name, prop_schema in value.items()
                }
            case "items":
                result["items"] = (
                    convert_to_gemini_schema(value, _defs)  # type: ignore[arg-type]
                    if isinstance(value, dict)
                    else value
                )
            case "anyOf":
                result["anyOf"] = [
                    convert_to_gemini_schema(variant, _defs) for variant in value
                ]
            case "$ref":
                # Resolve reference: e.g. "#/$defs/ModelName" -> inline.
                ref_name = value.rsplit("/", 1)[-1]
                if ref_name in _defs:
                    return convert_to_gemini_schema(_defs[ref_name], _defs)
            case _:
                result[key] = value

    return result


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
