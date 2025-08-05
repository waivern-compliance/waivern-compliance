"""Unit tests for PersonalDataAnalyser."""

from wct.analysers.personal_data_analyser.analyser import PersonalDataAnalyser


class TestPersonalDataAnalyser:
    """Test suite for PersonalDataAnalyser."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.analyser = PersonalDataAnalyser()

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        analyser = PersonalDataAnalyser()
        assert analyser.ruleset_name == "personal_data"
        assert analyser.evidence_context_size == "small"
        default_evidence_count = 3
        assert analyser.maximum_evidence_count == default_evidence_count
        assert analyser.enable_llm_validation is True

    def test_get_name(self):
        """Test analyser name retrieval."""
        assert PersonalDataAnalyser.get_name() == "personal_data_analyser"

    def test_from_properties(self):
        """Test analyser creation from properties dictionary."""
        properties = {
            "ruleset": "custom_personal_data",
            "evidence_context_size": "large",
            "maximum_evidence_count": 5,
            "enable_llm_validation": False,
        }

        analyser = PersonalDataAnalyser.from_properties(properties)
        assert analyser.ruleset_name == "custom_personal_data"
        assert analyser.evidence_context_size == "large"
        expected_evidence_count = 5
        assert analyser.maximum_evidence_count == expected_evidence_count
        assert analyser.enable_llm_validation is False

    def test_get_supported_input_schemas(self):
        """Test that supported input schemas are returned."""
        schemas = PersonalDataAnalyser.get_supported_input_schemas()
        assert len(schemas) > 0
        # Check that text schema is supported
        schema_names = [schema.name for schema in schemas]
        assert "text" in schema_names

    def test_get_supported_output_schemas(self):
        """Test that supported output schemas are returned."""
        schemas = PersonalDataAnalyser.get_supported_output_schemas()
        assert len(schemas) > 0
        # Check that personal_data_analysis_findings schema is supported
        schema_names = [schema.name for schema in schemas]
        assert "personal_data_analysis_findings" in schema_names

    # TODO: Add comprehensive tests for:
    # - process() method with different input formats
    # - _analyze_content() method
    # - _extract_evidence() method
    # - LLM validation functionality
    # - Error handling and edge cases
