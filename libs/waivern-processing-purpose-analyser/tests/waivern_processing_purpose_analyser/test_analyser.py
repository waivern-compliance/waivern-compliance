"""Unit tests for ProcessingPurposeAnalyser.

This test module focuses on testing the public API of ProcessingPurposeAnalyser,
following black-box testing principles and proper encapsulation. Each test class
encapsulates specific concerns and processing paths.
"""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.types import LLMValidationConfig, PatternMatchingConfig
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    FilesystemMetadata,
    RelationalDatabaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm import BaseLLMService

from waivern_processing_purpose_analyser.analyser import (
    ProcessingPurposeAnalyser,
)
from waivern_processing_purpose_analyser.pattern_matcher import (
    ProcessingPurposePatternMatcher,
)
from waivern_processing_purpose_analyser.types import (
    ProcessingPurposeAnalyserConfig,
)


class TestProcessingPurposeAnalyserInitialisation:
    """Test class for ProcessingPurposeAnalyser initialisation and configuration."""

    @pytest.fixture
    def valid_pattern_matching_config(self) -> PatternMatchingConfig:
        """Create valid pattern matching configuration."""
        return PatternMatchingConfig(
            ruleset="processing_purposes",
            evidence_context_size="medium",
            maximum_evidence_count=3,
        )

    @pytest.fixture
    def valid_config(
        self, valid_pattern_matching_config: PatternMatchingConfig
    ) -> ProcessingPurposeAnalyserConfig:
        """Create valid analyser configuration."""
        return ProcessingPurposeAnalyserConfig(
            pattern_matching=valid_pattern_matching_config,
            llm_validation=LLMValidationConfig(enable_llm_validation=False),
        )

    @pytest.fixture
    def pattern_matcher(
        self, valid_pattern_matching_config: PatternMatchingConfig
    ) -> ProcessingPurposePatternMatcher:
        """Create pattern matcher for testing."""
        return ProcessingPurposePatternMatcher(valid_pattern_matching_config)

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service for testing."""
        return Mock(spec=BaseLLMService)

    def test_init_creates_analyser_with_valid_configuration(
        self,
        valid_config: ProcessingPurposeAnalyserConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that __init__ creates analyser with valid configuration."""
        # Act
        analyser = ProcessingPurposeAnalyser(valid_config, mock_llm_service)

        # Assert - only verify object creation and public method availability
        assert analyser is not None
        assert hasattr(analyser, "process")
        assert callable(getattr(analyser, "process"))
        assert hasattr(analyser, "get_name")
        assert callable(getattr(analyser, "get_name"))

    def test_from_properties_creates_analyser_from_dict(
        self, mock_llm_service: Mock
    ) -> None:
        """Test that from_properties creates analyser from dictionary properties."""
        # Arrange
        properties = {
            "pattern_matching": {
                "ruleset": "processing_purposes",
                "evidence_context_size": "large",
                "maximum_evidence_count": 5,
            },
            "llm_validation": {"enable_llm_validation": True},
        }

        # Act
        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Assert
        assert analyser is not None
        assert isinstance(analyser, ProcessingPurposeAnalyser)

    def test_from_properties_handles_minimal_configuration(
        self, mock_llm_service: Mock
    ) -> None:
        """Test that from_properties handles minimal configuration with defaults."""
        # Arrange
        properties: dict[str, dict[str, str]] = {}

        # Act
        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Assert
        assert analyser is not None
        assert isinstance(analyser, ProcessingPurposeAnalyser)

    def test_from_properties_enables_llm_validation_by_default(
        self, mock_llm_service: Mock
    ) -> None:
        """Test that from_properties enables LLM validation by default."""
        # Arrange
        properties: dict[str, dict[str, str]] = {}

        # Act
        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Assert
        # Create a test message to verify LLM validation is enabled in metadata
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="LLM validation test",
            description="Test LLM validation default",
            source="test",
            metadata={},
            data=[],
        )
        message = Message(
            id="test_llm_default",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        result = analyser.process(
            [message],
            Schema("processing_purpose_finding", "1.0.0"),
        )
        metadata = result.content["analysis_metadata"]
        assert metadata["llm_validation_enabled"] is True

    def test_from_properties_respects_explicit_llm_validation_config(
        self, mock_llm_service: Mock
    ) -> None:
        """Test that from_properties respects explicit LLM validation configuration."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": False}}

        # Act
        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Assert
        # Create a test message to verify LLM validation is disabled in metadata
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="LLM validation disabled test",
            description="Test explicit LLM validation disabled",
            source="test",
            metadata={},
            data=[],
        )
        message = Message(
            id="test_llm_disabled",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        result = analyser.process(
            [message],
            Schema("processing_purpose_finding", "1.0.0"),
        )
        metadata = result.content["analysis_metadata"]
        assert metadata["llm_validation_enabled"] is False

    def test_get_name_returns_correct_analyser_name(self) -> None:
        """Test that get_name returns correct analyser name."""
        # Act
        name = ProcessingPurposeAnalyser.get_name()

        # Assert
        assert name == "processing_purpose_analyser"
        assert isinstance(name, str)


class TestProcessingPurposeAnalyserSchemaSupport:
    """Test class for schema support methods."""

    def test_get_input_requirements_returns_expected_schemas(self) -> None:
        """Test that get_input_requirements returns expected input schema combinations."""
        # Act
        requirements = ProcessingPurposeAnalyser.get_input_requirements()

        # Assert
        assert isinstance(requirements, list)
        assert len(requirements) > 0

        # Flatten to get all schema names (each inner list is an alternative)
        schema_names = set()
        for combination in requirements:
            for req in combination:
                schema_names.add(req.schema_name)

        assert "standard_input" in schema_names
        assert "source_code" in schema_names

    def test_get_supported_output_schemas_returns_processing_purpose_schema(
        self,
    ) -> None:
        """Test that get_supported_output_schemas returns processing purpose schema."""
        # Act
        schemas = ProcessingPurposeAnalyser.get_supported_output_schemas()

        # Assert
        assert isinstance(schemas, list)
        assert len(schemas) > 0

        # Verify processing purpose schema is present
        schema_names = {schema.name for schema in schemas}
        assert "processing_purpose_finding" in schema_names


class TestProcessingPurposeAnalyserStandardInputProcessing:
    """Test class for standard_input schema processing path."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service for testing."""
        return Mock(spec=BaseLLMService)

    @pytest.fixture
    def analyser(self, mock_llm_service: Mock) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        config = ProcessingPurposeAnalyserConfig.from_properties({})
        return ProcessingPurposeAnalyser(config, mock_llm_service)

    @pytest.fixture
    def standard_input_schema(self) -> Schema:
        """Create standard input schema."""
        return Schema("standard_input", "1.0.0")

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Create output schema."""
        return Schema("processing_purpose_finding", "1.0.0")

    @pytest.fixture
    def empty_standard_input_message(self, standard_input_schema: Schema) -> Message:
        """Create empty standard input message."""
        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Empty test",
            description="Empty test data",
            source="test",
            metadata={},
            data=[],
        )
        return Message(
            id="test_empty",
            content=data.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

    @pytest.fixture
    def simple_standard_input_message(self, standard_input_schema: Schema) -> Message:
        """Create simple standard input message with processing purpose patterns."""
        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Simple test",
            description="Simple test with patterns",
            source="test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Contact our customer support team for payment assistance",
                    metadata=BaseMetadata(source="test_data", connector_type="test"),
                ),
            ],
        )
        return Message(
            id="test_simple",
            content=data.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

    def test_process_standard_input_returns_valid_message_for_empty_data(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        empty_standard_input_message: Message,
    ) -> None:
        """Test that process returns valid message for empty standard input data."""
        # Act
        result = analyser.process([empty_standard_input_message], output_schema)

        # Assert
        assert isinstance(result, Message)
        assert result.schema == output_schema
        assert isinstance(result.content, dict)

        # Verify required structure
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)

    def test_process_standard_input_creates_findings_for_pattern_matches(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        simple_standard_input_message: Message,
    ) -> None:
        """Test that process creates findings for pattern matches in standard input."""
        # Act
        result = analyser.process([simple_standard_input_message], output_schema)

        # Assert
        assert isinstance(result, Message)
        findings = result.content["findings"]
        assert isinstance(findings, list)

        if len(findings) > 0:
            # Verify finding structure if patterns were matched
            finding = findings[0]
            assert "purpose" in finding
            assert "purpose_category" in finding
            assert "risk_level" in finding
            assert "compliance" in finding
            assert "matched_patterns" in finding
            assert "evidence" in finding
            assert "metadata" in finding

    def test_process_standard_input_creates_valid_summary(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        simple_standard_input_message: Message,
    ) -> None:
        """Test that process creates valid summary for standard input processing."""
        # Act
        result = analyser.process([simple_standard_input_message], output_schema)

        # Assert
        summary = result.content["summary"]
        findings = result.content["findings"]

        assert isinstance(summary, dict)
        assert "total_findings" in summary
        assert "purposes_identified" in summary
        assert "high_risk_count" in summary
        assert "purpose_categories" in summary
        assert "risk_level_distribution" in summary

        assert isinstance(summary["total_findings"], int)
        assert isinstance(summary["purposes_identified"], int)
        assert isinstance(summary["high_risk_count"], int)
        assert isinstance(summary["purpose_categories"], dict)
        assert isinstance(summary["risk_level_distribution"], dict)

        assert summary["total_findings"] >= 0
        assert summary["purposes_identified"] >= 0
        assert summary["high_risk_count"] >= 0

        risk_dist = summary["risk_level_distribution"]
        assert "low" in risk_dist and "medium" in risk_dist and "high" in risk_dist
        for count in risk_dist.values():
            assert isinstance(count, int) and count >= 0

        for category, count in summary["purpose_categories"].items():
            assert isinstance(category, str)
            assert isinstance(count, int) and count > 0

        assert summary["total_findings"] == len(findings)

        if len(findings) > 0:
            actual_unique_purposes = len(set(f["purpose"] for f in findings))
            assert summary["purposes_identified"] == actual_unique_purposes
            assert sum(risk_dist.values()) == summary["total_findings"]
            assert summary["high_risk_count"] == risk_dist["high"]
            if summary["purpose_categories"]:
                assert (
                    sum(summary["purpose_categories"].values())
                    == summary["total_findings"]
                )

    def test_process_standard_input_creates_valid_analysis_metadata(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        simple_standard_input_message: Message,
    ) -> None:
        """Test that process creates valid analysis metadata for standard input."""
        # Act
        result = analyser.process([simple_standard_input_message], output_schema)

        # Assert
        metadata = result.content["analysis_metadata"]
        assert isinstance(metadata, dict)

        assert "ruleset_used" in metadata
        assert "llm_validation_enabled" in metadata
        assert "evidence_context_size" in metadata
        assert "llm_validation_mode" in metadata
        assert "llm_batch_size" in metadata
        assert "analyser_version" in metadata
        assert "processing_purpose_categories_detected" in metadata

        assert isinstance(metadata["ruleset_used"], str)
        assert isinstance(metadata["llm_validation_enabled"], bool)
        assert isinstance(metadata["evidence_context_size"], str)
        assert isinstance(metadata["llm_validation_mode"], str)
        assert isinstance(metadata["llm_batch_size"], int)
        assert isinstance(metadata["analyser_version"], str)
        assert isinstance(metadata["processing_purpose_categories_detected"], int)

        assert metadata["llm_batch_size"] > 0
        assert len(metadata["analyser_version"]) > 0
        assert metadata["processing_purpose_categories_detected"] >= 0

    def test_process_standard_input_summary_handles_empty_findings(
        self,
        analyser: ProcessingPurposeAnalyser,
        standard_input_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that summary handles empty findings correctly."""
        # Arrange
        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="No patterns test",
            description="Content with no processing purpose patterns",
            source="test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="this text has no processing purpose keywords",
                    metadata=RelationalDatabaseMetadata(
                        source="test_source",
                        connector_type="mysql",
                        table_name="customers",
                        column_name="purpose_description",
                        schema_name="test_db",
                    ),
                )
            ],
        )
        message = Message(
            id="test_empty",
            content=data.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Act
        result = analyser.process([message], output_schema)

        # Assert
        summary = result.content["summary"]

        assert summary["total_findings"] == 0
        assert summary["purposes_identified"] == 0
        assert summary["high_risk_count"] == 0
        assert summary["purpose_categories"] == {}

        risk_dist = summary["risk_level_distribution"]
        assert risk_dist["low"] == 0
        assert risk_dist["medium"] == 0
        assert risk_dist["high"] == 0

    def test_process_standard_input_summary_handles_duplicate_purposes_correctly(
        self,
        analyser: ProcessingPurposeAnalyser,
        standard_input_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts unique purposes correctly when findings have duplicate purposes."""
        # Arrange - content that should generate multiple findings but potentially same purposes
        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Duplicate purposes test",
            description="Content that may generate duplicate processing purposes",
            source="test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="customer payment processing system",
                    metadata=BaseMetadata(source="system1", connector_type="test"),
                ),
                StandardInputDataItemModel(
                    content="process customer payments daily",
                    metadata=RelationalDatabaseMetadata(
                        source="system2",
                        connector_type="mysql",
                        table_name="orders",
                        column_name="purpose",
                        schema_name="ecommerce",
                    ),
                ),
                StandardInputDataItemModel(
                    content="customer service support portal",
                    metadata=BaseMetadata(source="system3", connector_type="test"),
                ),
            ],
        )
        message = Message(
            id="test_duplicate_purposes",
            content=data.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Act
        result = analyser.process([message], output_schema)

        # Assert
        findings = result.content["findings"]
        summary = result.content["summary"]

        if len(findings) > 0:
            # Verify purposes_identified counts unique purposes, not total findings
            actual_unique_purposes = len(set(f["purpose"] for f in findings))
            assert summary["purposes_identified"] == actual_unique_purposes
            assert summary["purposes_identified"] <= summary["total_findings"]


class TestProcessingPurposeAnalyserErrorHandling:
    """Test class for error handling and validation."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service for testing."""
        return Mock(spec=BaseLLMService)

    @pytest.fixture
    def analyser(self, mock_llm_service: Mock) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        config = ProcessingPurposeAnalyserConfig.from_properties({})
        return ProcessingPurposeAnalyser(config, mock_llm_service)

    @pytest.fixture
    def standard_input_schema(self) -> Schema:
        """Create standard input schema."""
        return Schema("standard_input", "1.0.0")

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Create output schema."""
        return Schema("processing_purpose_finding", "1.0.0")

    def test_process_raises_value_error_for_unsupported_input_schema(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
    ) -> None:
        """Test that process raises ValueError for unsupported input schema."""

        # Arrange - create a mock schema that validates but has unsupported name
        class UnsupportedSchema:
            def __init__(self) -> None:
                self.name = "unsupported_schema"
                self.version = "1.0.0"
                # Provide schema property to avoid validation error
                self.schema = {
                    "type": "object",
                    "properties": {"data": {"type": "array"}},
                }

        unsupported_schema = UnsupportedSchema()  # type: ignore

        # Create a valid message that will pass validation
        message = Message(
            id="test_unsupported",
            content={"data": []},
            schema=unsupported_schema,  # type: ignore
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported input schema"):
            analyser.process([message], output_schema)

    def test_process_creates_analysis_chain_entry(self) -> None:
        """Test that analyser creates proper analysis chain entry.

        Business Logic: Each analyser must create a chain entry to track
        the analysis for audit purposes and downstream processing.
        """
        # Arrange
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "llm_validation": {
                    "enable_llm_validation": False
                }  # Disable LLM for speed
            }
        )
        analyser = ProcessingPurposeAnalyser(config, llm_service=None)
        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("processing_purpose_finding", "1.0.0")

        message = Message(
            id="test_chain",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test data",
                "data": [
                    {
                        "content": "Contact our support team",
                        "metadata": {"source": "test", "connector_type": "test"},
                    }
                ],
            },
            schema=input_schema,
        )

        # Act
        result = analyser.process([message], output_schema)

        # Assert
        analysis_metadata = result.content["analysis_metadata"]
        analyses_chain = analysis_metadata["analyses_chain"]

        assert len(analyses_chain) == 1, "Should create exactly one chain entry"

        chain_entry = analyses_chain[0]
        assert chain_entry["order"] == 1, "Should start with order 1 for new analysis"
        assert chain_entry["analyser"] == "processing_purpose_analyser", (
            "Should identify correct analyser"
        )
        assert "execution_timestamp" in chain_entry, (
            "Should include execution timestamp"
        )


class TestProcessingPurposeAnalyserOutputValidation:
    """Test class for output message validation and structure."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service for testing."""
        return Mock(spec=BaseLLMService)

    @pytest.fixture
    def analyser(self, mock_llm_service: Mock) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        config = ProcessingPurposeAnalyserConfig.from_properties({})
        return ProcessingPurposeAnalyser(config, mock_llm_service)

    @pytest.fixture
    def standard_input_schema(self) -> Schema:
        """Create standard input schema."""
        return Schema("standard_input", "1.0.0")

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Create output schema."""
        return Schema("processing_purpose_finding", "1.0.0")

    @pytest.fixture
    def test_message(self, standard_input_schema: Schema) -> Message:
        """Create test message for validation testing."""
        data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Output validation test",
            description="Test output validation",
            source="test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Customer support and payment processing",
                    metadata=FilesystemMetadata(
                        source="test_validation",
                        connector_type="filesystem",
                        file_path="/test/validation.txt",
                    ),
                ),
            ],
        )
        return Message(
            id="test_output_validation",
            content=data.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

    def test_process_output_message_validates_against_schema(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        test_message: Message,
    ) -> None:
        """Test that process creates output message that validates against schema."""
        # Act
        result = analyser.process([test_message], output_schema)

        # Assert - if no exception is raised, validation passed
        assert isinstance(result, Message)
        assert result.schema == output_schema

        # Verify the message validates successfully
        result.validate()  # Should not raise exception

    def test_process_output_has_consistent_message_id(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        test_message: Message,
    ) -> None:
        """Test that process creates output with consistent message ID."""
        # Act
        result = analyser.process([test_message], output_schema)

        # Assert
        assert isinstance(result.id, str)
        assert len(result.id) > 0
        assert result.id == "Processing_purpose_analysis"

    def test_process_output_summary_reflects_findings_count(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        test_message: Message,
    ) -> None:
        """Test that output summary correctly reflects findings count."""
        # Act
        result = analyser.process([test_message], output_schema)

        # Assert
        content = result.content
        findings_count = len(content["findings"])
        summary_count = content["summary"]["total_findings"]

        assert summary_count == findings_count

        # Verify purposes identified count is logical
        if findings_count > 0:
            purposes_identified = content["summary"]["purposes_identified"]
            assert purposes_identified <= findings_count
            assert purposes_identified >= 0

    def test_null_values_omitted_from_json_output_standard_input(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        test_message: Message,
    ) -> None:
        """Test that null values are omitted from JSON output for standard input (all three fields null)."""
        # Act
        result = analyser.process([test_message], output_schema)

        # Assert - check that findings don't contain null fields
        content = result.content
        findings = content["findings"]

        for finding in findings:
            # These fields should not be present in the output when they are null
            assert "service_category" not in finding
            assert "collection_type" not in finding
            assert "data_source" not in finding


class TestProcessingPurposeAnalyserSourceCodeProcessing:
    """Test class for source_code schema processing path.

    TODO: These are stub tests that need implementation to verify the
    source_code input flow through the analyser end-to-end.
    """

    @pytest.fixture
    def analyser_no_llm(self) -> ProcessingPurposeAnalyser:
        """Create analyser without LLM validation for faster tests."""
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": False}}
        )
        return ProcessingPurposeAnalyser(config, llm_service=None)

    @pytest.fixture
    def source_code_schema(self) -> Schema:
        """Create source code schema."""
        return Schema("source_code", "1.0.0")

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Create output schema."""
        return Schema("processing_purpose_finding", "1.0.0")

    @pytest.mark.skip(reason="TODO: Implement source_code processing test")
    def test_process_source_code_returns_valid_message(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that process returns valid message for source_code input."""
        # TODO: Create source_code schema message with PHP code content
        # TODO: Call analyser.process([message], output_schema)
        # TODO: Assert valid message structure returned
        pass

    @pytest.mark.skip(reason="TODO: Implement source_code findings test")
    def test_process_source_code_creates_findings_from_patterns(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that source_code processing creates findings for matched patterns."""
        # TODO: Create source_code message with content that matches rulesets
        # TODO: Call analyser.process([message], output_schema)
        # TODO: Assert findings are created with correct purpose categories
        pass

    @pytest.mark.skip(reason="TODO: Implement source_code service integration test")
    def test_process_source_code_detects_service_integrations(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that source_code processing detects service integration patterns."""
        # TODO: Create source_code message with service integration patterns
        # TODO: Assert findings include service_category field
        pass

    @pytest.mark.skip(reason="TODO: Implement source_code data collection test")
    def test_process_source_code_detects_data_collection(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that source_code processing detects data collection patterns."""
        # TODO: Create source_code message with data collection patterns
        # TODO: Assert findings include collection_type and data_source fields
        pass

    @pytest.mark.skip(reason="TODO: Implement source_code structured elements test")
    def test_process_source_code_analyses_structured_elements(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that source_code processing analyses imports, functions, and classes."""
        # TODO: Create source_code message with structured elements (imports, functions, classes)
        # TODO: Assert findings are created from structured element analysis
        pass
