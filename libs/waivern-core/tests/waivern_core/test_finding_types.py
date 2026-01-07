"""Tests for custom logic in finding types.

These tests cover our custom code only:
- Custom validators (JSON serialisation, risk level)
- Custom methods (generate_json_schema)
- ClassVar version override behaviour

We do NOT test Pydantic's built-in functionality (min_length, extra="forbid", etc.)
as that is Pydantic's responsibility.
"""

import json
import tempfile
from pathlib import Path
from typing import ClassVar

import pytest
from pydantic import Field

from waivern_core.schemas import (
    BaseFindingMetadata,
    BaseSchemaOutput,
)


class TestBaseFindingMetadataCustomValidators:
    """Tests for custom validators in BaseFindingMetadata."""

    def test_context_must_be_json_serialisable(self) -> None:
        """Contract: context field must be JSON-serialisable for portable storage."""
        with pytest.raises(ValueError, match="context must be JSON-serialisable"):
            BaseFindingMetadata(
                source="test.txt",
                context={"invalid": object()},
            )

    def test_context_accepts_valid_json_types(self) -> None:
        """Contract: context accepts all standard JSON types."""
        metadata = BaseFindingMetadata(
            source="test.txt",
            context={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "array": [1, 2, 3],
                "nested": {"key": "value"},
            },
        )
        assert metadata.context["string"] == "value"


class TestBaseSchemaOutputGeneration:
    """Tests for JSON schema generation functionality."""

    def test_generate_json_schema_creates_valid_file(self) -> None:
        """Contract: generate_json_schema creates a valid JSON schema file."""

        class TestOutput(BaseSchemaOutput):
            name: str = Field(description="A name")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "schema.json"
            TestOutput.generate_json_schema(output_path)

            assert output_path.exists()
            with open(output_path) as f:
                schema = json.load(f)

            assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
            assert "properties" in schema

    def test_generate_json_schema_includes_version_from_classvar(self) -> None:
        """Contract: generated schema includes version from __schema_version__ ClassVar."""

        class VersionedOutput(BaseSchemaOutput):
            __schema_version__: ClassVar[str] = "2.5.0"
            data: str = Field(description="Data")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "schema.json"
            VersionedOutput.generate_json_schema(output_path)

            with open(output_path) as f:
                schema = json.load(f)

            assert schema["version"] == "2.5.0"

    def test_generate_json_schema_creates_parent_directories(self) -> None:
        """Contract: generate_json_schema creates parent directories if needed."""

        class SimpleOutput(BaseSchemaOutput):
            data: str = Field(description="Data")

        with tempfile.TemporaryDirectory() as tmpdir:
            deep_path = Path(tmpdir) / "a" / "b" / "c" / "schema.json"
            assert not deep_path.parent.exists()

            SimpleOutput.generate_json_schema(deep_path)

            assert deep_path.exists()

    def test_subclass_can_override_schema_version(self) -> None:
        """Contract: subclasses can define their own __schema_version__."""

        class V1Output(BaseSchemaOutput):
            __schema_version__: ClassVar[str] = "1.0.0"

        class V2Output(BaseSchemaOutput):
            __schema_version__: ClassVar[str] = "2.0.0"

        assert V1Output.__schema_version__ == "1.0.0"
        assert V2Output.__schema_version__ == "2.0.0"
        assert BaseSchemaOutput.__schema_version__ == "1.0.0"  # Base unchanged


class TestAnalysisChainEntryValidationFields:
    """Tests for optional LLM validation fields in AnalysisChainEntry."""

    def test_optional_fields_default_to_none(self) -> None:
        """New validation fields default to None when not provided."""
        from waivern_core.schemas import AnalysisChainEntry

        # Arrange & Act - create entry without validation fields
        entry = AnalysisChainEntry(order=1, analyser="test_analyser")

        # Assert - new fields should default to None
        assert entry.llm_validation_enabled is None
        assert entry.validation_statistics is None

    def test_serialisation_excludes_none_fields(self) -> None:
        """JSON serialisation excludes None validation fields for clean output."""
        from waivern_core.schemas import AnalysisChainEntry

        # Arrange - create entry without validation fields
        entry = AnalysisChainEntry(order=1, analyser="test_analyser")

        # Act - serialise with exclude_none
        serialised = entry.model_dump(mode="json", exclude_none=True)

        # Assert - validation fields should NOT be in output
        assert "llm_validation_enabled" not in serialised
        assert "validation_statistics" not in serialised
        # But required fields should still be present
        assert serialised["order"] == 1
        assert serialised["analyser"] == "test_analyser"
        assert "execution_timestamp" in serialised

    def test_accepts_validation_statistics_when_provided(self) -> None:
        """Chain entry accepts validation statistics when explicitly provided."""
        from waivern_core.schemas import AnalysisChainEntry, ChainEntryValidationStats

        # Arrange
        stats = ChainEntryValidationStats(
            original_findings_count=48,
            validated_findings_count=2,
            false_positives_removed=46,
            validation_mode="conservative",
        )

        # Act - create entry with validation fields
        entry = AnalysisChainEntry(
            order=1,
            analyser="personal_data_analyser",
            llm_validation_enabled=True,
            validation_statistics=stats,
        )

        # Assert - fields are set correctly
        assert entry.llm_validation_enabled is True
        assert entry.validation_statistics is not None
        assert entry.validation_statistics.original_findings_count == 48
        assert entry.validation_statistics.false_positives_removed == 46

        # Assert - serialisation includes the validation fields
        serialised = entry.model_dump(mode="json", exclude_none=True)
        assert serialised["llm_validation_enabled"] is True
        assert serialised["validation_statistics"]["original_findings_count"] == 48
