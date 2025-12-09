"""Tests for Analyser base class compliance framework declaration."""

from typing import override

from waivern_core import Analyser, InputRequirement, Message, Schema


class GenericAnalyser(Analyser):
    """Concrete generic analyser for testing base class behaviour."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "generic_test_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [[InputRequirement("standard_input", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("generic_finding", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        return Message(
            id="test",
            content={"test": "data"},
            schema=output_schema,
        )


class GdprSpecificAnalyser(Analyser):
    """GDPR-specific analyser for testing compliance framework override."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "gdpr_test_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [[InputRequirement("standard_input", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("gdpr_finding", "1.0.0")]

    @classmethod
    @override
    def get_compliance_frameworks(cls) -> list[str]:
        """Override to declare GDPR support."""
        return ["GDPR"]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        return Message(
            id="test",
            content={"test": "data"},
            schema=output_schema,
        )


class TestAnalyserComplianceFrameworks:
    """Test compliance framework declaration on Analyser base class."""

    def test_get_compliance_frameworks_returns_empty_list_by_default(self) -> None:
        """Default implementation returns empty list (generic analyser)."""
        # Act
        frameworks = GenericAnalyser.get_compliance_frameworks()

        # Assert
        assert frameworks == []
        assert isinstance(frameworks, list)

    def test_subclass_can_override_compliance_frameworks(self) -> None:
        """Subclasses can override to declare specific frameworks."""
        # Act
        frameworks = GdprSpecificAnalyser.get_compliance_frameworks()

        # Assert
        assert frameworks == ["GDPR"]
        assert isinstance(frameworks, list)

    def test_compliance_frameworks_is_classmethod(self) -> None:
        """get_compliance_frameworks can be called without instantiation."""
        # Act - call on class directly without creating instance
        frameworks = GenericAnalyser.get_compliance_frameworks()

        # Assert - should work without error
        assert isinstance(frameworks, list)
