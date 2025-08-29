"""Unit tests for ProcessingPurposeAnalyser.

This test module focuses on testing the public API of ProcessingPurposeAnalyser,
following black-box testing principles and proper encapsulation. Each test class
encapsulates specific concerns and processing paths.
"""

from unittest.mock import Mock

import pytest

from wct.analysers.processing_purpose_analyser.analyser import ProcessingPurposeAnalyser
from wct.analysers.processing_purpose_analyser.pattern_matcher import (
    ProcessingPurposePatternMatcher,
)
from wct.analysers.processing_purpose_analyser.types import (
    ProcessingPurposeAnalyserConfig,
)
from wct.analysers.types import LLMValidationConfig, PatternMatchingConfig
from wct.analysers.utilities import LLMServiceManager
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

    @pytest.fixture
    def mock_llm_service_manager(self) -> Mock:
        """Create mock LLM service manager for testing."""
        return Mock(spec=LLMServiceManager)

    def test_init_creates_analyser_with_valid_configuration(
        self,
        valid_config: ProcessingPurposeAnalyserConfig,
        pattern_matcher: ProcessingPurposePatternMatcher,
        mock_llm_service_manager: Mock,
    ) -> None:
        """Test that __init__ creates analyser with valid configuration."""
        # Act
        analyser = ProcessingPurposeAnalyser(
            valid_config, pattern_matcher, mock_llm_service_manager
        )

        # Assert - only verify object creation and public method availability
        assert analyser is not None
        assert hasattr(analyser, "process")
        assert callable(getattr(analyser, "process"))
        assert hasattr(analyser, "get_name")
        assert callable(getattr(analyser, "get_name"))

    def test_from_properties_creates_analyser_from_dict(
        self, mock_llm_service_manager: Mock
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
        analyser = ProcessingPurposeAnalyser.from_properties(properties)
        analyser.llm_service_manager = mock_llm_service_manager

        # Assert
        assert analyser is not None
        assert isinstance(analyser, ProcessingPurposeAnalyser)

    def test_from_properties_handles_minimal_configuration(
        self, mock_llm_service_manager: Mock
    ) -> None:
        """Test that from_properties handles minimal configuration with defaults."""
        # Arrange
        properties: dict[str, dict[str, str]] = {}

        # Act
        analyser = ProcessingPurposeAnalyser.from_properties(properties)
        analyser.llm_service_manager = mock_llm_service_manager

        # Assert
        assert analyser is not None
        assert isinstance(analyser, ProcessingPurposeAnalyser)

    def test_from_properties_enables_llm_validation_by_default(
        self, mock_llm_service_manager: Mock
    ) -> None:
        """Test that from_properties enables LLM validation by default."""
        # Arrange
        properties: dict[str, dict[str, str]] = {}

        # Act
        analyser = ProcessingPurposeAnalyser.from_properties(properties)
        analyser.llm_service_manager = mock_llm_service_manager

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
            schema=StandardInputSchema(),
        )

        result = analyser.process(
            StandardInputSchema(), ProcessingPurposeFindingSchema(), message
        )
        metadata = result.content["analysis_metadata"]
        assert metadata["llm_validation_enabled"] is True

    def test_from_properties_respects_explicit_llm_validation_config(
        self, mock_llm_service_manager: Mock
    ) -> None:
        """Test that from_properties respects explicit LLM validation configuration."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": False}}

        # Act
        analyser = ProcessingPurposeAnalyser.from_properties(properties)
        analyser.llm_service_manager = mock_llm_service_manager

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
            schema=StandardInputSchema(),
        )

        result = analyser.process(
            StandardInputSchema(), ProcessingPurposeFindingSchema(), message
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
    def mock_llm_service_manager(self) -> Mock:
        """Create mock LLM service manager for testing."""
        return Mock(spec=LLMServiceManager)

    @pytest.fixture
    def analyser(self, mock_llm_service_manager: Mock) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        analyser = ProcessingPurposeAnalyser.from_properties({})
        analyser.llm_service_manager = mock_llm_service_manager
        return analyser

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
            assert "compliance" in finding
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
        assert "llm_validation_mode" in metadata
        assert "llm_batch_size" in metadata
        assert "analyser_version" in metadata
        assert "input_schema" in metadata
        assert "processing_purpose_categories_detected" in metadata

        assert isinstance(metadata["ruleset_used"], str)
        assert isinstance(metadata["llm_validation_enabled"], bool)
        assert isinstance(metadata["evidence_context_size"], str)
        assert isinstance(metadata["llm_validation_mode"], str)
        assert isinstance(metadata["llm_batch_size"], int)
        assert isinstance(metadata["analyser_version"], str)
        assert isinstance(metadata["input_schema"], str)
        assert isinstance(metadata["processing_purpose_categories_detected"], int)

        assert metadata["llm_batch_size"] > 0
        assert len(metadata["analyser_version"]) > 0
        assert metadata["input_schema"] == "standard_input"
        assert metadata["processing_purpose_categories_detected"] >= 0

    def test_process_standard_input_summary_handles_empty_findings(
        self,
        analyser: ProcessingPurposeAnalyser,
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
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
                    metadata=StandardInputDataItemMetadataModel(source="test"),
                )
            ],
        )
        message = Message(
            id="test_empty",
            content=data.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Act
        result = analyser.process(standard_input_schema, output_schema, message)

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
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
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
                    metadata=StandardInputDataItemMetadataModel(source="system1"),
                ),
                StandardInputDataItemModel(
                    content="process customer payments daily",
                    metadata=StandardInputDataItemMetadataModel(source="system2"),
                ),
                StandardInputDataItemModel(
                    content="customer service support portal",
                    metadata=StandardInputDataItemMetadataModel(source="system3"),
                ),
            ],
        )
        message = Message(
            id="test_duplicate_purposes",
            content=data.model_dump(exclude_none=True),
            schema=standard_input_schema,
        )

        # Act
        result = analyser.process(standard_input_schema, output_schema, message)

        # Assert
        findings = result.content["findings"]
        summary = result.content["summary"]

        if len(findings) > 0:
            # Verify purposes_identified counts unique purposes, not total findings
            actual_unique_purposes = len(set(f["purpose"] for f in findings))
            assert summary["purposes_identified"] == actual_unique_purposes
            assert summary["purposes_identified"] <= summary["total_findings"]


class TestProcessingPurposeAnalyserSourceCodeProcessing:
    """Test class for source_code schema processing path."""

    @pytest.fixture
    def mock_llm_service_manager(self) -> Mock:
        """Create mock LLM service manager for testing."""
        return Mock(spec=LLMServiceManager)

    @pytest.fixture
    def analyser(self, mock_llm_service_manager: Mock) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        analyser = ProcessingPurposeAnalyser.from_properties({})
        analyser.llm_service_manager = mock_llm_service_manager
        return analyser

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
            assert "compliance" in finding
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
    def mock_llm_service_manager(self) -> Mock:
        """Create mock LLM service manager for testing."""
        return Mock(spec=LLMServiceManager)

    @pytest.fixture
    def analyser(self, mock_llm_service_manager: Mock) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        analyser = ProcessingPurposeAnalyser.from_properties({})
        analyser.llm_service_manager = mock_llm_service_manager
        return analyser

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
    def mock_llm_service_manager(self) -> Mock:
        """Create mock LLM service manager for testing."""
        return Mock(spec=LLMServiceManager)

    @pytest.fixture
    def analyser(self, mock_llm_service_manager: Mock) -> ProcessingPurposeAnalyser:
        """Create analyser instance for testing."""
        analyser = ProcessingPurposeAnalyser.from_properties({})
        analyser.llm_service_manager = mock_llm_service_manager
        return analyser

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

    def test_null_values_omitted_from_json_output_standard_input(
        self,
        analyser: ProcessingPurposeAnalyser,
        standard_input_schema: StandardInputSchema,
        output_schema: ProcessingPurposeFindingSchema,
        test_message: Message,
    ) -> None:
        """Test that null values are omitted from JSON output for standard input (all three fields null)."""
        # Act
        result = analyser.process(standard_input_schema, output_schema, test_message)

        # Assert - check that findings don't contain null fields
        content = result.content
        findings = content["findings"]

        for finding in findings:
            # These fields should not be present in the output when they are null
            assert "service_category" not in finding
            assert "collection_type" not in finding
            assert "data_source" not in finding

    def test_null_values_omitted_from_json_output_service_integration(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: ProcessingPurposeFindingSchema,
    ) -> None:
        """Test that null values are omitted for ServiceIntegrationRule (service_category populated, others null)."""
        # Arrange - create source code with service integration pattern
        source_code_schema = SourceCodeSchema()
        file_data = SourceCodeFileDataModel(
            file_path="/src/PaymentService.php",
            language="php",
            raw_content="<?php $aws_s3 = new AmazonS3Client();",  # Triggers service integration rule
            metadata=SourceCodeFileMetadataModel(
                file_size=50,
                line_count=1,
                last_modified="2024-01-01T00:00:00Z",
            ),
            functions=[],
            classes=[],
            imports=[],
        )

        data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Service integration test",
            description="Test service integration rule",
            language="php",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1,
                total_lines=1,
                analysis_timestamp="2024-01-01T00:00:00Z",
                parser_version="1.0.0",
            ),
            data=[file_data],
        )

        test_message = Message(
            id="test_service_integration",
            content=data.model_dump(exclude_none=True),
            schema=source_code_schema,
        )

        # Act
        result = analyser.process(source_code_schema, output_schema, test_message)

        # Assert
        content = result.content
        findings = content["findings"]

        # Should have findings from service integration rule
        service_integration_findings = [f for f in findings if "service_category" in f]
        assert len(service_integration_findings) > 0

        for finding in service_integration_findings:
            # service_category should be present and not null
            assert "service_category" in finding
            assert finding["service_category"] is not None
            # collection_type and data_source should not be present (they would be null)
            assert "collection_type" not in finding
            assert "data_source" not in finding

    def test_null_values_omitted_from_json_output_data_collection(
        self,
        analyser: ProcessingPurposeAnalyser,
        output_schema: ProcessingPurposeFindingSchema,
    ) -> None:
        """Test that null values are omitted for DataCollectionRule (collection_type and data_source populated, service_category null)."""
        # Arrange - create source code with data collection pattern
        source_code_schema = SourceCodeSchema()
        file_data = SourceCodeFileDataModel(
            file_path="/src/FormHandler.php",
            language="php",
            raw_content="<?php $data = $_POST['email'];",  # Triggers data collection rule
            metadata=SourceCodeFileMetadataModel(
                file_size=30,
                line_count=1,
                last_modified="2024-01-01T00:00:00Z",
            ),
            functions=[],
            classes=[],
            imports=[],
        )

        data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Data collection test",
            description="Test data collection rule",
            language="php",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1,
                total_lines=1,
                analysis_timestamp="2024-01-01T00:00:00Z",
                parser_version="1.0.0",
            ),
            data=[file_data],
        )

        test_message = Message(
            id="test_data_collection",
            content=data.model_dump(exclude_none=True),
            schema=source_code_schema,
        )

        # Act
        result = analyser.process(source_code_schema, output_schema, test_message)

        # Assert
        content = result.content
        findings = content["findings"]

        # Should have findings from data collection rule
        data_collection_findings = [f for f in findings if "collection_type" in f]
        assert len(data_collection_findings) > 0

        for finding in data_collection_findings:
            # collection_type and data_source should be present and not null
            assert "collection_type" in finding
            assert finding["collection_type"] is not None
            assert "data_source" in finding
            assert finding["data_source"] is not None
            # service_category should not be present (it would be null)
            assert "service_category" not in finding
