"""Unit tests for ProcessingPurposeAnalyser.

This test module focuses on testing the public API of ProcessingPurposeAnalyser,
following black-box testing principles and proper encapsulation. Each test class
encapsulates specific concerns and processing paths.
"""

import pytest

from wct.analysers.processing_purpose_analyser.analyser import ProcessingPurposeAnalyser
from wct.analysers.processing_purpose_analyser.pattern_matcher import (
    ProcessingPurposePatternMatcher,
)
from wct.analysers.processing_purpose_analyser.types import (
    ProcessingPurposeAnalyserConfig,
)
from wct.analysers.types import LLMValidationConfig, PatternMatchingConfig
from wct.message import Message
from wct.schemas import (
    ProcessingPurposeFindingSchema,
    SourceCodeAnalysisMetadataModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
    SourceCodeSchema,
    StandardInputDataItemMetadataModel,
    StandardInputDataItemModel,
    StandardInputDataModel,
    StandardInputSchema,
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

    def test_init_creates_analyser_with_valid_configuration(
        self,
        valid_config: ProcessingPurposeAnalyserConfig,
        pattern_matcher: ProcessingPurposePatternMatcher,
    ) -> None:
        """Test that __init__ creates analyser with valid configuration."""
        # Act
        analyser = ProcessingPurposeAnalyser(valid_config, pattern_matcher)

        # Assert - only verify object creation and public method availability
        assert analyser is not None
        assert hasattr(analyser, "process")
        assert callable(getattr(analyser, "process"))
        assert hasattr(analyser, "get_name")
        assert callable(getattr(analyser, "get_name"))

    def test_from_properties_creates_analyser_from_dict(self) -> None:
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
        analyser = ProcessingPurposeAnalyser.from_properties(properties)

        # Assert
        assert analyser is not None
        assert isinstance(analyser, ProcessingPurposeAnalyser)

    def test_from_properties_handles_minimal_configuration(self) -> None:
        """Test that from_properties handles minimal configuration with defaults."""
        # Arrange
        properties: dict[str, dict[str, str]] = {}

        # Act
        analyser = ProcessingPurposeAnalyser.from_properties(properties)

        # Assert
        assert analyser is not None
        assert isinstance(analyser, ProcessingPurposeAnalyser)

    def test_get_name_returns_correct_analyser_name(self) -> None:
        """Test that get_name returns correct analyser name."""
        # Act
        name = ProcessingPurposeAnalyser.get_name()

        # Assert
        assert name == "processing_purpose_analyser"
        assert isinstance(name, str)


class TestProcessingPurposeAnalyserSchemaSupport:
    """Test class for schema support methods."""

    def test_get_supported_input_schemas_returns_expected_schemas(self) -> None:
        """Test that get_supported_input_schemas returns expected input schemas."""
        # Act
        schemas = ProcessingPurposeAnalyser.get_supported_input_schemas()

        # Assert
        assert isinstance(schemas, list)
        assert len(schemas) > 0

        # Verify expected schema names are present
        schema_names = {schema.name for schema in schemas}
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
    def analyser(self) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        return ProcessingPurposeAnalyser.from_properties({})

    @pytest.fixture
    def standard_input_schema(self) -> StandardInputSchema:
        """Create standard input schema."""
        return StandardInputSchema()

    @pytest.fixture
    def output_schema(self) -> ProcessingPurposeFindingSchema:
        """Create output schema."""
        return ProcessingPurposeFindingSchema()

    @pytest.fixture
    def empty_standard_input_message(
        self, standard_input_schema: StandardInputSchema
    ) -> Message:
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
    def simple_standard_input_message(
        self, standard_input_schema: StandardInputSchema
    ) -> Message:
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
                    metadata=StandardInputDataItemMetadataModel(source="test_data"),
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
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
        empty_standard_input_message: Message,
    ) -> None:
        """Test that process returns valid message for empty standard input data."""
        # Act
        result = analyser.process(
            standard_input_schema, output_schema, empty_standard_input_message
        )

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
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
        simple_standard_input_message: Message,
    ) -> None:
        """Test that process creates findings for pattern matches in standard input."""
        # Act
        result = analyser.process(
            standard_input_schema, output_schema, simple_standard_input_message
        )

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
            assert "compliance_relevance" in finding
            assert "matched_pattern" in finding
            assert "evidence" in finding
            assert "metadata" in finding

    def test_process_standard_input_creates_valid_summary(
        self,
        analyser: ProcessingPurposeAnalyser,
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
        simple_standard_input_message: Message,
    ) -> None:
        """Test that process creates valid summary for standard input processing."""
        # Act
        result = analyser.process(
            standard_input_schema, output_schema, simple_standard_input_message
        )

        # Assert
        summary = result.content["summary"]
        assert isinstance(summary, dict)
        assert "total_findings" in summary
        assert "purposes_identified" in summary
        assert isinstance(summary["total_findings"], int)
        assert isinstance(summary["purposes_identified"], int)
        assert summary["total_findings"] >= 0
        assert summary["purposes_identified"] >= 0

    def test_process_standard_input_creates_valid_analysis_metadata(
        self,
        analyser: ProcessingPurposeAnalyser,
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
        simple_standard_input_message: Message,
    ) -> None:
        """Test that process creates valid analysis metadata for standard input."""
        # Act
        result = analyser.process(
            standard_input_schema, output_schema, simple_standard_input_message
        )

        # Assert
        metadata = result.content["analysis_metadata"]
        assert isinstance(metadata, dict)
        assert "ruleset_used" in metadata
        assert "llm_validation_enabled" in metadata
        assert "evidence_context_size" in metadata
        assert isinstance(metadata["ruleset_used"], str)
        assert isinstance(metadata["llm_validation_enabled"], bool)
        assert isinstance(metadata["evidence_context_size"], str)


class TestProcessingPurposeAnalyserSourceCodeProcessing:
    """Test class for source_code schema processing path."""

    @pytest.fixture
    def analyser(self) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        return ProcessingPurposeAnalyser.from_properties({})

    @pytest.fixture
    def source_code_schema(self) -> SourceCodeSchema:
        """Create source code schema."""
        return SourceCodeSchema()

    @pytest.fixture
    def output_schema(self) -> ProcessingPurposeFindingSchema:
        """Create output schema."""
        return ProcessingPurposeFindingSchema()

    @pytest.fixture
    def empty_source_code_message(
        self, source_code_schema: SourceCodeSchema
    ) -> Message:
        """Create empty source code message."""
        data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Empty source code test",
            description="Empty source code analysis",
            language="php",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=0,
                total_lines=0,
                analysis_timestamp="2024-01-01T00:00:00Z",
                parser_version="1.0.0",
            ),
            data=[],
        )
        return Message(
            id="test_empty_source",
            content=data.model_dump(exclude_none=True),
            schema=source_code_schema,
        )

    @pytest.fixture
    def simple_source_code_message(
        self, source_code_schema: SourceCodeSchema
    ) -> Message:
        """Create simple source code message with processing purpose patterns."""
        file_data = SourceCodeFileDataModel(
            file_path="/src/PaymentService.php",
            language="php",
            raw_content="""<?php
class PaymentService {
    public function processPayment($amount) {
        // Process customer payment
        return $this->gateway->charge($amount);
    }
}
""",
            metadata=SourceCodeFileMetadataModel(
                file_size=256,
                line_count=8,
                last_modified="2024-01-01T00:00:00Z",
                complexity_score=2.0,
            ),
            functions=[],
            classes=[],
            imports=[],
        )

        data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Payment service analysis",
            description="Source code analysis for payment service",
            language="php",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1,
                total_lines=8,
                analysis_timestamp="2024-01-01T00:00:00Z",
                parser_version="1.0.0",
            ),
            data=[file_data],
        )
        return Message(
            id="test_source_code",
            content=data.model_dump(exclude_none=True),
            schema=source_code_schema,
        )

    def test_process_source_code_returns_valid_message_for_empty_data(
        self,
        analyser: ProcessingPurposeAnalyser,
        source_code_schema: SourceCodeSchema,
        output_schema: ProcessingPurposeFindingSchema,
        empty_source_code_message: Message,
    ) -> None:
        """Test that process returns valid message for empty source code data."""
        # Act
        result = analyser.process(
            source_code_schema, output_schema, empty_source_code_message
        )

        # Assert
        assert isinstance(result, Message)
        assert result.schema == output_schema
        assert isinstance(result.content, dict)

        # Verify required structure
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)

    def test_process_source_code_creates_findings_for_pattern_matches(
        self,
        analyser: ProcessingPurposeAnalyser,
        source_code_schema: SourceCodeSchema,
        output_schema: ProcessingPurposeFindingSchema,
        simple_source_code_message: Message,
    ) -> None:
        """Test that process creates findings for pattern matches in source code."""
        # Act
        result = analyser.process(
            source_code_schema, output_schema, simple_source_code_message
        )

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
            assert "compliance_relevance" in finding
            assert "matched_pattern" in finding
            assert "evidence" in finding
            assert "metadata" in finding

    def test_process_source_code_handles_multiple_files(
        self,
        analyser: ProcessingPurposeAnalyser,
        source_code_schema: SourceCodeSchema,
        output_schema: ProcessingPurposeFindingSchema,
    ) -> None:
        """Test that process handles multiple source code files correctly."""
        # Arrange
        file1 = SourceCodeFileDataModel(
            file_path="/src/PaymentService.php",
            language="php",
            raw_content="<?php class PaymentService { public function processPayment() {} }",
            metadata=SourceCodeFileMetadataModel(
                file_size=128,
                line_count=4,
                last_modified="2024-01-01T00:00:00Z",
                complexity_score=1.0,
            ),
            functions=[],
            classes=[],
            imports=[],
        )

        file2 = SourceCodeFileDataModel(
            file_path="/src/SupportService.php",
            language="php",
            raw_content="<?php class SupportService { public function contactSupport() {} }",
            metadata=SourceCodeFileMetadataModel(
                file_size=128,
                line_count=4,
                last_modified="2024-01-01T00:00:00Z",
                complexity_score=1.0,
            ),
            functions=[],
            classes=[],
            imports=[],
        )

        data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Multi-file analysis",
            description="Analysis of multiple files",
            language="php",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=2,
                total_lines=8,
                analysis_timestamp="2024-01-01T00:00:00Z",
                parser_version="1.0.0",
            ),
            data=[file1, file2],
        )

        message = Message(
            id="test_multi_file",
            content=data.model_dump(exclude_none=True),
            schema=source_code_schema,
        )

        # Act
        result = analyser.process(source_code_schema, output_schema, message)

        # Assert
        assert isinstance(result, Message)
        assert isinstance(result.content["findings"], list)
        assert isinstance(result.content["summary"], dict)


class TestProcessingPurposeAnalyserErrorHandling:
    """Test class for error handling and validation."""

    @pytest.fixture
    def analyser(self) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        return ProcessingPurposeAnalyser.from_properties({})

    @pytest.fixture
    def standard_input_schema(self) -> StandardInputSchema:
        """Create standard input schema."""
        return StandardInputSchema()

    @pytest.fixture
    def source_code_schema(self) -> SourceCodeSchema:
        """Create source code schema."""
        return SourceCodeSchema()

    @pytest.fixture
    def output_schema(self) -> ProcessingPurposeFindingSchema:
        """Create output schema."""
        return ProcessingPurposeFindingSchema()

    def test_process_raises_value_error_for_unsupported_input_schema(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: ProcessingPurposeFindingSchema,
    ) -> None:
        """Test that process raises ValueError for unsupported input schema."""

        # Arrange - create a mock schema that validates but has unsupported name
        class UnsupportedSchema:
            def __init__(self) -> None:
                self.name = "unsupported_schema"
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
            analyser.process(unsupported_schema, output_schema, message)  # type: ignore

    def test_from_properties_handles_invalid_configuration_gracefully(self) -> None:
        """Test that from_properties handles invalid configuration data."""
        # Arrange
        invalid_properties = {
            "pattern_matching": {
                "ruleset": 123,  # Invalid type - should be string
                "evidence_context_size": "invalid_size",
            }
        }

        # Act & Assert
        # Should raise validation error due to invalid configuration
        with pytest.raises((ValueError, TypeError)):
            ProcessingPurposeAnalyser.from_properties(invalid_properties)


class TestProcessingPurposeAnalyserOutputValidation:
    """Test class for output message validation and structure."""

    @pytest.fixture
    def analyser(self) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        return ProcessingPurposeAnalyser.from_properties({})

    @pytest.fixture
    def standard_input_schema(self) -> StandardInputSchema:
        """Create standard input schema."""
        return StandardInputSchema()

    @pytest.fixture
    def output_schema(self) -> ProcessingPurposeFindingSchema:
        """Create output schema."""
        return ProcessingPurposeFindingSchema()

    @pytest.fixture
    def test_message(self, standard_input_schema: StandardInputSchema) -> Message:
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
                    metadata=StandardInputDataItemMetadataModel(
                        source="test_validation"
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
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
        test_message: Message,
    ) -> None:
        """Test that process creates output message that validates against schema."""
        # Act
        result = analyser.process(standard_input_schema, output_schema, test_message)

        # Assert - if no exception is raised, validation passed
        assert isinstance(result, Message)
        assert result.schema == output_schema

        # Verify the message validates successfully
        result.validate()  # Should not raise exception

    def test_process_output_has_consistent_message_id(
        self,
        analyser: ProcessingPurposeAnalyser,
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
        test_message: Message,
    ) -> None:
        """Test that process creates output with consistent message ID."""
        # Act
        result = analyser.process(standard_input_schema, output_schema, test_message)

        # Assert
        assert isinstance(result.id, str)
        assert len(result.id) > 0
        assert result.id == "Processing_purpose_analysis"

    def test_process_output_summary_reflects_findings_count(
        self,
        analyser: ProcessingPurposeAnalyser,
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
        test_message: Message,
    ) -> None:
        """Test that output summary correctly reflects findings count."""
        # Act
        result = analyser.process(standard_input_schema, output_schema, test_message)

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
