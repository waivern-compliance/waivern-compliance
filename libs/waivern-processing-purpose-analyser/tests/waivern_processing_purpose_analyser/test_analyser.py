"""Unit tests for ProcessingPurposeAnalyser.

This test module focuses on testing the public API of ProcessingPurposeAnalyser,
following black-box testing principles and proper encapsulation. Each test class
encapsulates specific concerns and processing paths.
"""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.types import (
    EvidenceContextSize,
    LLMValidationConfig,
    PatternMatchingConfig,
)
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
            ruleset="local/processing_purposes/1.0.0",
            evidence_context_size=EvidenceContextSize.MEDIUM,
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
                "ruleset": "local/processing_purposes/1.0.0",
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

    def test_from_properties_disables_llm_validation_by_default(
        self, mock_llm_service: Mock
    ) -> None:
        """Test that from_properties disables LLM validation by default."""
        # Arrange
        properties: dict[str, dict[str, str]] = {}

        # Act
        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Assert
        # Create a test message to verify LLM validation is disabled in metadata
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
        assert metadata["llm_validation_enabled"] is False

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
        assert "purpose_categories" in summary

        assert isinstance(summary["total_findings"], int)
        assert isinstance(summary["purposes_identified"], int)
        assert isinstance(summary["purpose_categories"], dict)

        assert summary["total_findings"] >= 0
        assert summary["purposes_identified"] >= 0

        for category, count in summary["purpose_categories"].items():
            assert isinstance(category, str)
            assert isinstance(count, int) and count > 0

        assert summary["total_findings"] == len(findings)

        if len(findings) > 0:
            actual_unique_purposes = len(set(f["purpose"] for f in findings))
            assert summary["purposes_identified"] == actual_unique_purposes
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
        assert "analyser_version" in metadata

        assert isinstance(metadata["ruleset_used"], str)
        assert isinstance(metadata["llm_validation_enabled"], bool)
        assert isinstance(metadata["evidence_context_size"], str)
        assert isinstance(metadata["llm_validation_mode"], str)
        assert isinstance(metadata["analyser_version"], str)

        assert len(metadata["analyser_version"]) > 0

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
        assert summary["purpose_categories"] == {}

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

    def test_process_output_has_timestamped_message_id(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: Schema,
        test_message: Message,
    ) -> None:
        """Test that process creates output with timestamped message ID."""
        # Act
        result = analyser.process([test_message], output_schema)

        # Assert
        assert isinstance(result.id, str)
        assert len(result.id) > 0
        assert result.id.startswith("processing_purpose_analysis_")

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

    This test class verifies the end-to-end integration of source_code schema
    input through the analyser pipeline. Detailed pattern matching behaviour
    is tested in test_source_code_schema_input_handler.py.
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

    @pytest.fixture
    def source_code_message(self, source_code_schema: Schema) -> Message:
        """Create a valid source_code schema message with processing purpose patterns."""
        content = {
            "schemaVersion": "1.0.0",
            "name": "Test PHP Analysis",
            "description": "Test source code analysis for processing purposes",
            "language": "php",
            "source": "test_repo",
            "metadata": {
                "total_files": 1,
                "total_lines": 15,
                "analysis_timestamp": "2025-01-01T00:00:00Z",
            },
            "data": [
                {
                    "file_path": "/src/CustomerService.php",
                    "language": "php",
                    "raw_content": """<?php
class CustomerService {
    public function processPayment($amount) {
        // Process customer payment
        return $this->paymentGateway->charge($amount);
    }

    public function sendSupportEmail($message) {
        // Send support email to customer
        return $this->emailService->send($message);
    }
}
""",
                    "metadata": {
                        "file_size": 350,
                        "line_count": 15,
                        "last_modified": "2025-01-01T00:00:00Z",
                    },
                }
            ],
        }
        return Message(
            id="test_source_code",
            content=content,
            schema=source_code_schema,
        )

    def test_process_source_code_returns_valid_message(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_message: Message,
        output_schema: Schema,
    ) -> None:
        """Test that process returns valid message for source_code input.

        This end-to-end test verifies the full pipeline:
        - source_code schema input is accepted
        - Pattern matching generates findings
        - Output message has correct structure (findings, summary, analysis_metadata)
        - Output validates against processing_purpose_finding schema
        """
        # Act
        result = analyser_no_llm.process([source_code_message], output_schema)

        # Assert - Message structure
        assert isinstance(result, Message)
        assert result.schema == output_schema
        assert isinstance(result.content, dict)

        # Assert - Required top-level fields
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content

        # Assert - Findings structure
        findings = result.content["findings"]
        assert isinstance(findings, list)
        assert len(findings) > 0, "Should detect patterns in PHP code"

        # Assert - Summary structure
        summary = result.content["summary"]
        assert isinstance(summary, dict)
        assert "total_findings" in summary
        assert "purposes_identified" in summary
        assert "purpose_categories" in summary
        assert summary["total_findings"] == len(findings)

        # Assert - Analysis metadata structure
        metadata = result.content["analysis_metadata"]
        assert isinstance(metadata, dict)
        assert "ruleset_used" in metadata
        assert "llm_validation_enabled" in metadata
        assert metadata["llm_validation_enabled"] is False
        assert "analyser_version" in metadata

        # Assert - Output validates against schema
        result.validate()  # Should not raise


# =============================================================================
# Fan-in Tests (multiple input aggregation)
# =============================================================================


class TestFanInSupport:
    """Test suite for fan-in support (aggregating data from multiple input messages).

    Fan-in allows multiple upstream artifacts (e.g., multiple database connectors)
    to feed into a single ProcessingPurposeAnalyser, with all data items merged
    before processing.
    """

    @pytest.fixture
    def analyser_no_llm(self) -> ProcessingPurposeAnalyser:
        """Create analyser without LLM validation for faster tests."""
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": False}}
        )
        return ProcessingPurposeAnalyser(config, llm_service=None)

    @pytest.fixture
    def standard_input_schema(self) -> Schema:
        """Create standard input schema."""
        return Schema("standard_input", "1.0.0")

    @pytest.fixture
    def source_code_schema(self) -> Schema:
        """Create source code schema."""
        return Schema("source_code", "1.0.0")

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Create output schema."""
        return Schema("processing_purpose_finding", "1.0.0")

    # -------------------------------------------------------------------------
    # Standard Input Fan-in Tests
    # -------------------------------------------------------------------------

    def test_process_aggregates_findings_from_multiple_standard_input_messages(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        standard_input_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that findings from multiple standard_input messages are combined."""
        # Arrange - Message 1: payment-related content (distinct from message 2)
        data_1 = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Database 1",
            description="First database source",
            source="mysql://db1",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Process payment transactions for billing",
                    metadata=BaseMetadata(
                        source="db1_payments", connector_type="mysql"
                    ),
                ),
            ],
        )
        message_1 = Message(
            id="input_1",
            content=data_1.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Arrange - Message 2: marketing content (distinct from message 1)
        data_2 = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Database 2",
            description="Second database source",
            source="mysql://db2",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Marketing campaign analytics and tracking",
                    metadata=BaseMetadata(
                        source="db2_marketing", connector_type="mysql"
                    ),
                ),
            ],
        )
        message_2 = Message(
            id="input_2",
            content=data_2.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Act - process both messages together
        result = analyser_no_llm.process([message_1, message_2], output_schema)

        # Assert - findings should include results from BOTH messages
        findings = result.content["findings"]

        # Extract unique sources from finding metadata
        sources = {f["metadata"]["source"] for f in findings}

        # CRITICAL: Must have findings from BOTH sources
        assert "db1_payments" in sources, (
            "Should have findings from message 1 (db1_payments)"
        )
        assert "db2_marketing" in sources, (
            "Should have findings from message 2 (db2_marketing)"
        )

    def test_process_recalculates_summary_for_aggregated_standard_input_findings(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        standard_input_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that summary statistics reflect ALL findings from all standard_input messages."""
        # Arrange - Message 1: payment content
        data_1 = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Database 1",
            description="First database",
            source="db1",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Process payment transactions",
                    metadata=BaseMetadata(source="db1_table", connector_type="mysql"),
                ),
            ],
        )
        message_1 = Message(
            id="input_1",
            content=data_1.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Arrange - Message 2: marketing content
        data_2 = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Database 2",
            description="Second database",
            source="db2",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Marketing analytics tracking",
                    metadata=BaseMetadata(source="db2_table", connector_type="mysql"),
                ),
            ],
        )
        message_2 = Message(
            id="input_2",
            content=data_2.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Act
        result = analyser_no_llm.process([message_1, message_2], output_schema)

        # Assert - summary should reflect ALL findings from both messages
        findings = result.content["findings"]
        summary = result.content["summary"]

        assert summary["total_findings"] == len(findings)
        assert summary["total_findings"] >= 2, "Should have findings from both messages"

    def test_process_preserves_metadata_from_each_standard_input_message(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        standard_input_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that each finding retains metadata tracing to its original source."""
        # Arrange - Two messages with distinct, traceable metadata
        data_1 = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Database 1",
            description="First database",
            source="db1",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Process payment transactions",
                    metadata=RelationalDatabaseMetadata(
                        source="orders_db",
                        connector_type="mysql",
                        table_name="payments",
                        column_name="description",
                        schema_name="ecommerce",
                    ),
                ),
            ],
        )
        message_1 = Message(
            id="input_1",
            content=data_1.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        data_2 = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Database 2",
            description="Second database",
            source="db2",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Marketing campaign analytics",
                    metadata=RelationalDatabaseMetadata(
                        source="analytics_db",
                        connector_type="postgresql",
                        table_name="campaigns",
                        column_name="purpose",
                        schema_name="marketing",
                    ),
                ),
            ],
        )
        message_2 = Message(
            id="input_2",
            content=data_2.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Act
        result = analyser_no_llm.process([message_1, message_2], output_schema)

        # Assert - findings should preserve their original metadata
        findings = result.content["findings"]
        sources = {f["metadata"]["source"] for f in findings}

        # Verify metadata from both original sources is preserved
        assert "orders_db" in sources, "Should preserve metadata from message 1"
        assert "analytics_db" in sources, "Should preserve metadata from message 2"

    # -------------------------------------------------------------------------
    # Source Code Fan-in Tests
    # -------------------------------------------------------------------------

    def test_process_aggregates_findings_from_multiple_source_code_messages(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that findings from multiple source_code messages are combined."""
        # Arrange - Message 1: payment service file
        # Use word-boundary-compatible patterns (underscore as separator)
        content_1 = {
            "schemaVersion": "1.0.0",
            "name": "Repo 1",
            "description": "First repository",
            "source": "repo1",
            "metadata": {
                "total_files": 1,
                "total_lines": 10,
                "analysis_timestamp": "2025-01-01T00:00:00Z",
            },
            "data": [
                {
                    "file_path": "/repo1/PaymentService.php",
                    "language": "php",
                    "raw_content": "<?php\nclass PaymentService {\n    // Handle payment processing\n    public function process_payment() {}\n}\n",
                    "metadata": {"file_size": 100, "line_count": 5},
                }
            ],
        }
        message_1 = Message(
            id="source_1",
            content=content_1,
            schema=source_code_schema,
        )

        # Arrange - Message 2: analytics service file
        # Use word-boundary-compatible patterns (standalone word in comment)
        content_2 = {
            "schemaVersion": "1.0.0",
            "name": "Repo 2",
            "description": "Second repository",
            "source": "repo2",
            "metadata": {
                "total_files": 1,
                "total_lines": 10,
                "analysis_timestamp": "2025-01-01T00:00:00Z",
            },
            "data": [
                {
                    "file_path": "/repo2/AnalyticsService.php",
                    "language": "php",
                    "raw_content": "<?php\nclass AnalyticsService {\n    // Track analytics for users\n    public function track_analytics() {}\n}\n",
                    "metadata": {"file_size": 100, "line_count": 5},
                }
            ],
        }
        message_2 = Message(
            id="source_2",
            content=content_2,
            schema=source_code_schema,
        )

        # Act - process both messages together
        result = analyser_no_llm.process([message_1, message_2], output_schema)

        # Assert - findings should include results from BOTH files
        findings = result.content["findings"]

        # Extract unique file paths from finding metadata
        file_paths = {f["metadata"]["source"] for f in findings}

        # CRITICAL: Must have findings from BOTH source files
        assert "/repo1/PaymentService.php" in file_paths, (
            "Should have findings from message 1 (PaymentService.php)"
        )
        assert "/repo2/AnalyticsService.php" in file_paths, (
            "Should have findings from message 2 (AnalyticsService.php)"
        )

    def test_process_recalculates_summary_for_aggregated_source_code_findings(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that summary statistics reflect ALL findings from all source_code messages."""
        # Arrange - Message 1: payment service
        # Use word-boundary-compatible patterns (underscore as separator)
        content_1 = {
            "schemaVersion": "1.0.0",
            "name": "Repo 1",
            "description": "First repository",
            "source": "repo1",
            "metadata": {
                "total_files": 1,
                "total_lines": 10,
                "analysis_timestamp": "2025-01-01T00:00:00Z",
            },
            "data": [
                {
                    "file_path": "/repo1/PaymentService.php",
                    "language": "php",
                    "raw_content": "<?php\nclass PaymentService {\n    // Handle payment processing\n    public function process_payment() {}\n}\n",
                    "metadata": {"file_size": 100, "line_count": 5},
                }
            ],
        }
        message_1 = Message(id="source_1", content=content_1, schema=source_code_schema)

        # Arrange - Message 2: analytics service
        # Use word-boundary-compatible patterns (standalone word in comment)
        content_2 = {
            "schemaVersion": "1.0.0",
            "name": "Repo 2",
            "description": "Second repository",
            "source": "repo2",
            "metadata": {
                "total_files": 1,
                "total_lines": 10,
                "analysis_timestamp": "2025-01-01T00:00:00Z",
            },
            "data": [
                {
                    "file_path": "/repo2/AnalyticsService.php",
                    "language": "php",
                    "raw_content": "<?php\nclass AnalyticsService {\n    // Track analytics for users\n    public function track_analytics() {}\n}\n",
                    "metadata": {"file_size": 100, "line_count": 5},
                }
            ],
        }
        message_2 = Message(id="source_2", content=content_2, schema=source_code_schema)

        # Act
        result = analyser_no_llm.process([message_1, message_2], output_schema)

        # Assert - summary should reflect ALL findings
        findings = result.content["findings"]
        summary = result.content["summary"]

        assert summary["total_findings"] == len(findings)
        assert summary["total_findings"] >= 2, "Should have findings from both messages"

    def test_process_preserves_file_paths_from_each_source_code_message(
        self,
        analyser_no_llm: ProcessingPurposeAnalyser,
        source_code_schema: Schema,
        output_schema: Schema,
    ) -> None:
        """Test that each finding references the correct file path from its original message."""
        # Arrange - Two messages with files from different repositories
        content_1 = {
            "schemaVersion": "1.0.0",
            "name": "Frontend Repo",
            "description": "Frontend repository",
            "source": "frontend",
            "metadata": {
                "total_files": 1,
                "total_lines": 10,
                "analysis_timestamp": "2025-01-01T00:00:00Z",
            },
            "data": [
                {
                    "file_path": "/frontend/src/PaymentForm.tsx",
                    "language": "typescript",
                    "raw_content": "// Payment form component\nfunction processPayment() {}",
                    "metadata": {"file_size": 100, "line_count": 2},
                }
            ],
        }
        message_1 = Message(id="source_1", content=content_1, schema=source_code_schema)

        content_2 = {
            "schemaVersion": "1.0.0",
            "name": "Backend Repo",
            "description": "Backend repository",
            "source": "backend",
            "metadata": {
                "total_files": 1,
                "total_lines": 10,
                "analysis_timestamp": "2025-01-01T00:00:00Z",
            },
            "data": [
                {
                    "file_path": "/backend/api/analytics.py",
                    "language": "python",
                    "raw_content": "# Analytics module\ndef track_analytics(): pass",
                    "metadata": {"file_size": 100, "line_count": 2},
                }
            ],
        }
        message_2 = Message(id="source_2", content=content_2, schema=source_code_schema)

        # Act
        result = analyser_no_llm.process([message_1, message_2], output_schema)

        # Assert - findings should reference their original file paths
        findings = result.content["findings"]
        file_paths = {f["metadata"]["source"] for f in findings}

        # Verify file paths from both repositories are preserved
        assert "/frontend/src/PaymentForm.tsx" in file_paths, (
            "Should preserve file path from frontend repo"
        )
        assert "/backend/api/analytics.py" in file_paths, (
            "Should preserve file path from backend repo"
        )
