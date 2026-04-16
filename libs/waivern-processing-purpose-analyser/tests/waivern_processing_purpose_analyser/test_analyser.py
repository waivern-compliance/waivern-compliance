"""Metadata and construction tests for ProcessingPurposeAnalyser.

Behavioural coverage of the prepare/finalise distributed-processor contract
lives in ``test_distributed.py``. Pattern-matching behaviour lives in
``test_pattern_matcher.py``. Schema-specific reading is tested in
``test_source_code_schema_input_handler.py``.
"""

from waivern_processing_purpose_analyser.analyser import ProcessingPurposeAnalyser
from waivern_processing_purpose_analyser.types import ProcessingPurposeAnalyserConfig


class TestProcessingPurposeAnalyserIdentity:
    """Analyser identity and construction."""

    def test_get_name_returns_correct_analyser_name(self) -> None:
        assert ProcessingPurposeAnalyser.get_name() == "processing_purpose_analyser"

    def test_from_properties_creates_instance_with_defaults(self) -> None:
        config = ProcessingPurposeAnalyserConfig.from_properties({})

        analyser = ProcessingPurposeAnalyser(config)

        assert isinstance(analyser, ProcessingPurposeAnalyser)


class TestProcessingPurposeAnalyserSchemaSupport:
    """Static schema declarations."""

    def test_get_input_requirements_covers_standard_input_and_source_code(self) -> None:
        requirements = ProcessingPurposeAnalyser.get_input_requirements()
        schema_names = {
            req.schema_name for combination in requirements for req in combination
        }

        assert "standard_input" in schema_names
        assert "source_code" in schema_names

    def test_get_supported_output_schemas_returns_processing_purpose_indicator(
        self,
    ) -> None:
        schemas = ProcessingPurposeAnalyser.get_supported_output_schemas()
        schema_names = {schema.name for schema in schemas}

        assert "processing_purpose_indicator" in schema_names
