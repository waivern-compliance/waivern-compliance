"""Tests for Classifier base class framework declaration."""

from typing import override

from waivern_core import InputRequirement, Message, Schema
from waivern_core.base_classifier import Classifier


class GDPRClassifier(Classifier):
    """Concrete GDPR classifier for testing base class behaviour."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "gdpr_classifier"

    @classmethod
    @override
    def get_framework(cls) -> str:
        return "GDPR"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [[InputRequirement("personal_data_finding", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("gdpr_classified_finding", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        return Message(
            id="test",
            content={"classified": True},
            schema=output_schema,
        )


class TestClassifierFrameworkDeclaration:
    """Test framework declaration on Classifier base class."""

    def test_get_framework_returns_declared_framework(self) -> None:
        """Classifier declares its target framework."""
        framework = GDPRClassifier.get_framework()

        assert framework == "GDPR"
