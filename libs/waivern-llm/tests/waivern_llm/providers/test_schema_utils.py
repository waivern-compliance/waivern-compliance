"""Tests for schema utility functions.

Business behaviour: Transforms JSON schemas to meet provider-specific
requirements (e.g., Gemini's capitalised type names and $ref resolution).
"""

from waivern_llm.providers._schema_utils import convert_to_gemini_schema

# =============================================================================
# convert_to_gemini_schema
# =============================================================================


class TestConvertToGeminiSchema:
    """Tests for Gemini schema conversion."""

    def test_capitalises_type_names_for_objects_arrays_and_primitives(self) -> None:
        """Type names are capitalised recursively across all schema levels."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        }

        result = convert_to_gemini_schema(schema)

        assert result["type"] == "OBJECT"
        assert result["properties"]["name"]["type"] == "STRING"
        assert result["properties"]["count"]["type"] == "INTEGER"
        assert result["properties"]["score"]["type"] == "NUMBER"
        assert result["properties"]["active"]["type"] == "BOOLEAN"
        assert result["properties"]["tags"]["type"] == "ARRAY"
        assert result["properties"]["tags"]["items"]["type"] == "STRING"

    def test_resolves_ref_and_strips_defs(self) -> None:
        """$ref references are inlined and $defs removed from root."""
        schema = {
            "type": "object",
            "properties": {
                "child": {"$ref": "#/$defs/Inner"},
            },
            "$defs": {
                "Inner": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                    },
                },
            },
        }

        result = convert_to_gemini_schema(schema)

        # $defs should be absent
        assert "$defs" not in result

        # $ref should be resolved — child is now the inlined Inner definition
        child = result["properties"]["child"]
        assert "$ref" not in child
        assert child["type"] == "OBJECT"
        assert child["properties"]["value"]["type"] == "STRING"

    def test_strips_title_and_default(self) -> None:
        """title and default fields are removed at all levels."""
        schema = {
            "title": "RootModel",
            "type": "object",
            "properties": {
                "name": {"title": "Name", "type": "string", "default": "unknown"},
                "items": {
                    "title": "Items",
                    "type": "array",
                    "items": {"title": "Item", "type": "string"},
                },
            },
        }

        result = convert_to_gemini_schema(schema)

        assert "title" not in result
        assert "title" not in result["properties"]["name"]
        assert "default" not in result["properties"]["name"]
        assert "title" not in result["properties"]["items"]
        assert "title" not in result["properties"]["items"]["items"]

    def test_preserves_description_enum_and_required(self) -> None:
        """Supported fields (description, enum, required) pass through."""
        schema = {
            "type": "object",
            "description": "A classification result",
            "required": ["status", "category"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["TRUE_POSITIVE", "FALSE_POSITIVE"],
                    "description": "Classification outcome",
                },
                "category": {"type": "string"},
            },
        }

        result = convert_to_gemini_schema(schema)

        assert result["description"] == "A classification result"
        assert result["required"] == ["status", "category"]
        assert result["properties"]["status"]["enum"] == [
            "TRUE_POSITIVE",
            "FALSE_POSITIVE",
        ]
        assert result["properties"]["status"]["description"] == "Classification outcome"

    def test_handles_any_of_with_ref_and_null(self) -> None:
        """Pydantic Optional pattern (anyOf with $ref and null) is handled."""
        schema = {
            "type": "object",
            "properties": {
                "metadata": {
                    "anyOf": [
                        {"$ref": "#/$defs/Meta"},
                        {"type": "null"},
                    ],
                },
            },
            "$defs": {
                "Meta": {
                    "type": "object",
                    "properties": {"key": {"type": "string"}},
                },
            },
        }

        result = convert_to_gemini_schema(schema)

        # anyOf should be preserved with resolved branches
        any_of = result["properties"]["metadata"]["anyOf"]
        assert len(any_of) == 2

        # First branch: resolved $ref (Meta inlined)
        assert any_of[0]["type"] == "OBJECT"
        assert any_of[0]["properties"]["key"]["type"] == "STRING"

        # Second branch: null type capitalised
        assert any_of[1]["type"] == "NULL"

        # No $defs or $ref remain
        assert "$defs" not in result
        assert "$ref" not in result["properties"]["metadata"]

    def test_does_not_mutate_original_schema(self) -> None:
        """Original schema dict is not modified."""
        import copy

        schema = {
            "title": "Root",
            "type": "object",
            "properties": {
                "child": {"$ref": "#/$defs/Inner"},
            },
            "$defs": {
                "Inner": {
                    "title": "Inner",
                    "type": "object",
                    "properties": {"v": {"type": "string", "default": "x"}},
                },
            },
        }
        original = copy.deepcopy(schema)

        convert_to_gemini_schema(schema)

        assert schema == original

    def test_converts_real_pydantic_model_json_schema(self) -> None:
        """End-to-end conversion of actual Pydantic model_json_schema() output."""
        from typing import Literal

        from pydantic import BaseModel, Field

        class ValidationResult(BaseModel):
            finding_id: str = Field(description="ID of the finding")
            validation_result: Literal["TRUE_POSITIVE", "FALSE_POSITIVE"]
            confidence: float

        class ValidationResponse(BaseModel):
            results: list[ValidationResult] = Field(description="List of results")

        schema = ValidationResponse.model_json_schema()
        result = convert_to_gemini_schema(schema)

        # Root: OBJECT, no $defs, no $ref, no title
        assert result["type"] == "OBJECT"
        assert "$defs" not in result
        assert "title" not in result

        # results: ARRAY with inlined item schema
        results_prop = result["properties"]["results"]
        assert results_prop["type"] == "ARRAY"
        assert results_prop["description"] == "List of results"

        item = results_prop["items"]
        assert item["type"] == "OBJECT"
        assert "$ref" not in item
        assert "title" not in item

        # Verify fields on the inlined ValidationResult
        assert item["properties"]["finding_id"]["type"] == "STRING"
        assert item["properties"]["confidence"]["type"] == "NUMBER"
        assert item["properties"]["validation_result"]["enum"] == [
            "TRUE_POSITIVE",
            "FALSE_POSITIVE",
        ]
