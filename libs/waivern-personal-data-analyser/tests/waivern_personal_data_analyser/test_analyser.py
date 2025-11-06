"""Unit tests for PersonalDataAnalyser.

This test module focuses on testing the public API of PersonalDataAnalyser,
following black-box testing principles and proper encapsulation.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest
from waivern_analysers_shared.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_core import Analyser, RuleComplianceData
from waivern_core.errors import MessageValidationError
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseFindingCompliance,
    BaseFindingEvidence,
    Schema,
)
from waivern_core.schemas.base import SchemaLoadError
from waivern_llm import BaseLLMService
from waivern_rulesets.personal_data import PersonalDataRule

from waivern_personal_data_analyser.analyser import (
    PersonalDataAnalyser,
)
from waivern_personal_data_analyser.pattern_matcher import (
    PersonalDataPatternMatcher,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataFindingMetadata,
    PersonalDataFindingModel,
)
from waivern_personal_data_analyser.types import (
    PersonalDataAnalyserConfig,
)


class TestPersonalDataAnalyser:
    """Test suite for PersonalDataAnalyser."""

    # Test constants - defined locally, not imported from implementation
    EXPECTED_ANALYSER_NAME = "personal_data_analyser"
    EXPECTED_OUTPUT_MESSAGE_ID = "Personal_data_analysis"
    HIGH_RISK_LEVEL = "high"
    MEDIUM_RISK_LEVEL = "medium"
    LOW_RISK_LEVEL = "low"

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create a mock LLM service."""
        return Mock(spec=BaseLLMService)

    @pytest.fixture
    def valid_config(self) -> PersonalDataAnalyserConfig:
        """Create a valid configuration for testing using direct instantiation."""
        return PersonalDataAnalyserConfig(
            pattern_matching=PatternMatchingConfig(
                ruleset="personal_data",
                evidence_context_size="medium",
                maximum_evidence_count=5,
            ),
            llm_validation=LLMValidationConfig(
                enable_llm_validation=True,
                llm_batch_size=10,
                llm_validation_mode="standard",
            ),
        )

    @pytest.fixture
    def sample_input_data(self) -> dict[str, Any]:
        """Create sample input data in standard_input schema format."""
        return {
            "schemaVersion": "1.0.0",
            "name": "Test personal data analysis",
            "data": [
                {
                    "content": "Contact us at support@example.com or call 123-456-7890",
                    "metadata": {
                        "source": "contact_form.html",
                        "connector_type": "filesystem",
                    },
                },
                {
                    "content": "User profile: john.doe@company.com, phone: +44-20-1234-5678",
                    "metadata": {
                        "source": "user_database",
                        "connector_type": "test",
                        "table": "users",
                    },
                },
            ],
        }

    @pytest.fixture
    def sample_input_message(self, sample_input_data: dict[str, Any]) -> Message:
        """Create a sample input message for testing."""
        return Message(
            id="test_input",
            content=sample_input_data,
            schema=Schema("standard_input", "1.0.0"),
        )

    @pytest.fixture
    def mock_schema_modules(self) -> tuple[Mock, Mock]:
        """Create mock reader and producer modules for testing dynamic loading.

        Returns:
            Tuple of (mock_reader_module, mock_producer_module) configured
            with appropriate return values for process() testing.

        """
        # Setup mock reader module
        mock_reader = Mock()
        mock_reader.read.return_value = Mock(
            data=[],
            schemaVersion="1.0.0",
            name="test",
            description=None,
            contentEncoding=None,
            source=None,
            metadata={},
        )

        # Setup mock producer module
        mock_producer = Mock()
        mock_producer.produce.return_value = {
            "findings": [],
            "summary": {
                "total_findings": 0,
                "high_risk_count": 0,
                "special_category_count": 0,
            },
            "analysis_metadata": {
                "ruleset_used": "personal_data",
                "llm_validation_enabled": True,
                "evidence_context_size": "medium",
                "analyses_chain": [{"order": 1, "analyser": "personal_data_analyser"}],
            },
        }

        return mock_reader, mock_producer

    @pytest.fixture
    def sample_findings(self) -> list[PersonalDataFindingModel]:
        """Create sample personal data findings for testing."""
        return [
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level=self.MEDIUM_RISK_LEVEL,
                special_category=False,
                matched_patterns=["support@example.com"],
                compliance=[
                    BaseFindingCompliance(
                        regulation="GDPR",
                        relevance="Article 6 personal data processing",
                    )
                ],  # TODO: Add proper compliance framework mappings
                evidence=[
                    BaseFindingEvidence(content="Contact us at support@example.com")
                ],
                metadata=PersonalDataFindingMetadata(source="contact_form.html"),
            ),
            PersonalDataFindingModel(
                type="phone",
                data_type="basic_profile",
                risk_level=self.HIGH_RISK_LEVEL,
                special_category=False,
                matched_patterns=["123-456-7890"],
                compliance=[
                    BaseFindingCompliance(
                        regulation="GDPR",
                        relevance="Article 6 personal data processing",
                    )
                ],  # TODO: Add proper compliance framework mappings
                evidence=[BaseFindingEvidence(content="call 123-456-7890")],
                metadata=PersonalDataFindingMetadata(source="contact_form.html"),
            ),
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level=self.MEDIUM_RISK_LEVEL,
                special_category=False,
                matched_patterns=["john.doe@company.com"],
                compliance=[
                    BaseFindingCompliance(
                        regulation="GDPR",
                        relevance="Article 6 personal data processing",
                    )
                ],  # TODO: Add proper compliance framework mappings
                evidence=[BaseFindingEvidence(content="john.doe@company.com")],
                metadata=PersonalDataFindingMetadata(source="user_database"),
            ),
        ]

    def test_get_name_returns_correct_analyser_name(self) -> None:
        """Test that get_name returns the expected analyser name."""
        # Act
        name = PersonalDataAnalyser.get_name()

        # Assert
        assert name == self.EXPECTED_ANALYSER_NAME

    def test_get_supported_input_schemas_returns_standard_input(self) -> None:
        """Test that the analyser supports standard_input schema."""
        # Act
        input_schemas = PersonalDataAnalyser.get_supported_input_schemas()

        # Assert
        assert len(input_schemas) == 1
        assert input_schemas[0].name == "standard_input"
        assert input_schemas[0].version == "1.0.0"

    def test_get_supported_output_schemas_returns_personal_data_finding(self) -> None:
        """Test that the analyser outputs personal_data_finding schema."""
        # Act
        output_schemas = PersonalDataAnalyser.get_supported_output_schemas()

        # Assert
        assert len(output_schemas) == 1
        assert output_schemas[0].name == "personal_data_finding"
        assert output_schemas[0].version == "1.0.0"

    def test_process_returns_valid_output_message_with_findings(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that process returns valid output message with minimal required findings structure."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        # Mock LLM validation strategy to return sample findings
        # (Real pattern matcher will run, then LLM validation returns our test findings)
        with patch(
            "waivern_personal_data_analyser.analyser.personal_data_validation_strategy",
            return_value=(sample_findings, True),
        ):
            input_schema = Schema("standard_input", "1.0.0")
            output_schema = Schema("personal_data_finding", "1.0.0")

            # Act
            result_message = analyser.process(
                input_schema, output_schema, sample_input_message
            )

            # Assert - Basic message structure
            assert isinstance(result_message, Message)
            assert result_message.id == self.EXPECTED_OUTPUT_MESSAGE_ID
            assert result_message.schema == output_schema

            # Verify findings structure exists (count may vary based on real pattern matching)
            result_content = result_message.content
            assert "findings" in result_content
            assert "summary" in result_content
            assert isinstance(result_content["findings"], list)

            # Verify summary statistics structure
            summary = result_content["summary"]
            assert "total_findings" in summary
            assert "high_risk_count" in summary
            assert "special_category_count" in summary
            assert summary["total_findings"] == len(result_content["findings"])  # type: ignore[arg-type]

    def test_process_findings_include_expected_metadata_and_categorical_info(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that findings include source metadata and data_type categorical information."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        with patch(
            "waivern_personal_data_analyser.analyser.personal_data_validation_strategy",
            return_value=(sample_findings, True),
        ):
            input_schema = Schema("standard_input", "1.0.0")
            output_schema = Schema("personal_data_finding", "1.0.0")

            # Act
            result_message = analyser.process(
                input_schema, output_schema, sample_input_message
            )

            # Assert - Verify source field and data_type categorical information are included
            result_content = result_message.content
            for finding in result_content["findings"]:
                # Test source field directly
                assert finding["metadata"]["source"] in [
                    "contact_form.html",
                    "user_database",
                ]

                # Test data_type categorical information
                assert "data_type" in finding, (
                    "PersonalDataFindingModel should include data_type field for categorical reference"
                )
                assert isinstance(finding["data_type"], str)
                assert finding["data_type"] != "", "data_type should not be empty"

    def test_personal_data_analyser_provides_standardised_analysis_metadata(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that personal data analyser provides standardised analysis metadata.

        Business Logic: All analysers must provide consistent metadata for
        downstream processing and analysis chaining capabilities.
        """
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        # Mock LLM validation to return sample findings
        with patch(
            "waivern_personal_data_analyser.analyser.personal_data_validation_strategy",
            return_value=(sample_findings, True),
        ):
            input_schema = Schema("standard_input", "1.0.0")
            output_schema = Schema("personal_data_finding", "1.0.0")

            # Act
            result_message = analyser.process(
                input_schema, output_schema, sample_input_message
            )

        # Assert - Verify analysis_metadata exists and has core standardised fields
        result_content = result_message.content
        assert "analysis_metadata" in result_content, (
            "Personal data analyser must provide analysis_metadata for chaining support"
        )

        analysis_metadata = result_content["analysis_metadata"]

        # Core standardised fields required for analysis chaining
        assert "ruleset_used" in analysis_metadata
        assert "llm_validation_enabled" in analysis_metadata
        assert "evidence_context_size" in analysis_metadata
        assert "analyses_chain" in analysis_metadata

        # Verify field types and values match business requirements
        assert isinstance(analysis_metadata["ruleset_used"], str)
        assert isinstance(analysis_metadata["llm_validation_enabled"], bool)
        assert isinstance(analysis_metadata["analyses_chain"], list)
        assert len(analysis_metadata["analyses_chain"]) >= 1, (
            "analyses_chain must have at least one entry as it's mandatory"
        )
        assert analysis_metadata["ruleset_used"] == "personal_data"

    def test_process_includes_validation_summary_when_llm_validation_enabled(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that validation summary is included when LLM validation is enabled."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        # Mock LLM validation to return filtered findings (simulating false positive removal)
        filtered_findings = [sample_findings[0]]  # Return only one finding
        with patch(
            "waivern_personal_data_analyser.analyser.personal_data_validation_strategy",
            return_value=(filtered_findings, True),
        ):
            input_schema = Schema("standard_input", "1.0.0")
            output_schema = Schema("personal_data_finding", "1.0.0")

            # Act
            result_message = analyser.process(
                input_schema, output_schema, sample_input_message
            )

            # Assert - Verify validation summary is included if LLM validation runs
            result_content = result_message.content

            # Validation summary only added when original_findings > 0
            # (LLM validation skipped if no patterns found)
            if result_content["summary"]["total_findings"] > 0:
                assert "validation_summary" in result_content

                validation_summary = result_content["validation_summary"]
                assert validation_summary["llm_validation_enabled"] is True
                assert "original_findings_count" in validation_summary
                assert "validated_findings_count" in validation_summary
                assert "false_positives_removed" in validation_summary
                assert (
                    validation_summary["validated_findings_count"] == 1
                )  # LLM mock returns 1
                assert validation_summary["false_positives_removed"] == (
                    validation_summary["original_findings_count"] - 1
                )  # Verify calculation
                assert validation_summary["validation_mode"] == "standard"
            else:
                # If no patterns found, validation summary not included
                assert "validation_summary" not in result_content

    def test_process_excludes_validation_summary_when_llm_validation_disabled(
        self,
        mock_llm_service: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that validation summary is excluded when LLM validation is disabled."""
        # Arrange - using from_properties to demonstrate the flexibility
        config_with_llm_disabled = PersonalDataAnalyserConfig.from_properties(
            {
                "llm_validation": {"enable_llm_validation": False}
                # pattern_matching will use defaults
            }
        )
        analyser = PersonalDataAnalyser(
            config_with_llm_disabled,
            llm_service=None,
        )

        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("personal_data_finding", "1.0.0")

        # Act
        result_message = analyser.process(
            input_schema, output_schema, sample_input_message
        )

        # Assert
        result_content = result_message.content
        assert "validation_summary" not in result_content

    def test_process_excludes_validation_summary_when_no_findings(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that validation summary is excluded when no findings are present."""
        # Arrange - use config with LLM validation disabled to avoid calling LLM
        config_no_llm = PersonalDataAnalyserConfig.from_properties(
            {
                "llm_validation": {"enable_llm_validation": False}
                # pattern_matching will use defaults
            }
        )
        analyser = PersonalDataAnalyser(
            config_no_llm,
            llm_service=None,
        )

        # Create message with data that won't match any patterns
        empty_message = Message(
            id="test_empty",
            content={
                "schemaVersion": "1.0.0",
                "name": "Empty test data",
                "data": [
                    {
                        "content": "no patterns here",
                        "metadata": {"source": "test", "connector_type": "test"},
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("personal_data_finding", "1.0.0")

        # Act
        result_message = analyser.process(input_schema, output_schema, empty_message)

        # Assert
        result_content = result_message.content
        assert "validation_summary" not in result_content
        assert result_content["summary"]["total_findings"] == 0

    def test_process_handles_empty_data_gracefully(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that process handles empty input data gracefully."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        empty_input_data: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "name": "Empty test data",
            "data": [],
        }
        empty_message = Message(
            id="empty_test",
            content=empty_input_data,
            schema=Schema("standard_input", "1.0.0"),
        )

        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("personal_data_finding", "1.0.0")

        # Act
        result_message = analyser.process(input_schema, output_schema, empty_message)

        # Assert - Verify analyser handles empty data correctly
        assert isinstance(result_message, Message)
        result_content = result_message.content
        assert result_content["findings"] == []
        assert result_content["summary"]["total_findings"] == 0
        assert result_content["summary"]["high_risk_count"] == 0
        assert result_content["summary"]["special_category_count"] == 0

    def test_process_raises_error_with_invalid_schema(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that process raises error when message schema doesn't match expected."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        # Create message with wrong schema
        wrong_message = Message(
            id="test_wrong_schema",
            content={"some": "data"},
            schema=Schema(
                "source_code", "1.0.0"
            ),  # Wrong schema - expected standard_input
        )

        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("personal_data_finding", "1.0.0")

        # Act & Assert
        with pytest.raises(
            SchemaLoadError,
            match="Message schema .* does not match expected input schema",
        ):
            analyser.process(input_schema, output_schema, wrong_message)

    def test_validate_input_message_passes_with_matching_schema_names(self) -> None:
        """Test that validate_input_message passes when schema names match."""
        # Arrange
        message = Message(
            id="test_message",
            content={"schemaVersion": "1.0.0", "name": "test", "data": []},
            schema=Schema("standard_input", "1.0.0"),
        )
        expected_schema = Schema("standard_input", "1.0.0")

        # Act & Assert - should not raise any exception
        Analyser.validate_input_message(message, expected_schema)

    def test_validate_input_message_raises_error_when_message_has_no_schema(
        self,
    ) -> None:
        """Test that validate_input_message raises error when message has no schema."""
        # Arrange
        message = Message(
            id="test_message",
            content={"schemaVersion": "1.0.0", "name": "test", "data": []},
            schema=None,  # No schema attached
        )
        expected_schema = Schema("standard_input", "1.0.0")

        # Act & Assert - should raise MessageValidationError
        with pytest.raises(
            MessageValidationError, match="No schema provided for validation"
        ):
            Analyser.validate_input_message(message, expected_schema)

    def test_validate_input_message_passes_with_valid_message_content(self) -> None:
        """Test that validate_input_message passes when message content is valid."""
        # Arrange - create message with comprehensive valid standard_input content
        valid_content = {
            "schemaVersion": "1.0.0",
            "name": "Comprehensive test data",
            "data": [
                {
                    "content": "User email: john.doe@example.com, Phone: +1-555-123-4567",
                    "metadata": {
                        "source": "user_profile.html",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "extraction_method": "html_parser",
                    },
                },
                {
                    "content": "Contact support at help@company.com or call our hotline",
                    "metadata": {
                        "source": "contact_page.html",
                        "section": "footer",
                        "confidence": 0.95,
                    },
                },
            ],
        }
        message = Message(
            id="test_message",
            content=valid_content,
            schema=Schema("standard_input", "1.0.0"),
        )
        expected_schema = Schema("standard_input", "1.0.0")

        # Act & Assert - should not raise any exception
        Analyser.validate_input_message(message, expected_schema)

    def test_validate_input_message_raises_error_with_invalid_message_content(
        self,
    ) -> None:
        """Test that validate_input_message raises error when message content is invalid."""
        # Arrange - create message with invalid content (missing required fields)
        invalid_content: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            # Missing required 'name' field
            "data": [],
        }
        message = Message(
            id="test_message",
            content=invalid_content,
            schema=Schema("standard_input", "1.0.0"),
        )
        expected_schema = Schema("standard_input", "1.0.0")

        # Act & Assert - should raise MessageValidationError due to schema validation failure
        with pytest.raises(MessageValidationError, match="Schema validation failed"):
            Analyser.validate_input_message(message, expected_schema)

    def test_validate_input_message_raises_error_with_malformed_data_structure(
        self,
    ) -> None:
        """Test that validate_input_message raises error with completely malformed data."""
        # Arrange - create message with completely wrong structure
        malformed_content = {
            "wrong_field": "wrong_value",
            "data": "should_be_array_not_string",
        }
        message = Message(
            id="test_message",
            content=malformed_content,
            schema=Schema("standard_input", "1.0.0"),
        )
        expected_schema = Schema("standard_input", "1.0.0")

        # Act & Assert - should raise MessageValidationError
        with pytest.raises(MessageValidationError, match="Schema validation failed"):
            Analyser.validate_input_message(message, expected_schema)

    def test_personal_data_finding_data_type_matches_rule_data_type(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that finding.data_type matches the rule.data_type it was processed against."""
        # Arrange
        # Create a mock rule with known data_type
        mock_rule = PersonalDataRule(
            name="Test Email Detection",
            description="Test rule for email detection",
            patterns=("email",),
            data_type="basic_profile",  # This should appear in finding.data_type
            special_category=False,
            risk_level="medium",
            compliance=[
                RuleComplianceData(
                    regulation="GDPR",
                    relevance="Article 6 personal data processing",
                )
            ],
        )

        # Create real pattern matcher and mock its ruleset manager
        pattern_matcher = PersonalDataPatternMatcher(valid_config.pattern_matching)
        with patch.object(
            pattern_matcher.ruleset_manager, "get_rules", return_value=[mock_rule]
        ):
            analyser = PersonalDataAnalyser(
                valid_config,
                llm_service=None,  # Disable LLM validation
            )

            # Create input with content that matches our rule pattern
            input_content = {
                "schemaVersion": "1.0.0",
                "name": "Test data with email",
                "data": [
                    {
                        "content": "Please provide your email address",
                        "metadata": {
                            "source": "test.html",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            }
            test_message = Message(
                id="test_data_type",
                content=input_content,
                schema=Schema("standard_input", "1.0.0"),
            )

            input_schema = Schema("standard_input", "1.0.0")
            output_schema = Schema("personal_data_finding", "1.0.0")

            # Act
            result_message = analyser.process(input_schema, output_schema, test_message)

            # Assert - verify that finding.data_type matches rule.data_type
            result_content = result_message.content
            findings = result_content["findings"]
            assert len(findings) > 0, "Should have at least one finding"

            for finding in findings:
                assert finding["data_type"] == "basic_profile", (
                    f"Finding data_type should match rule.data_type, got: {finding.get('data_type')}"
                )

    def test_process_creates_analysis_chain_entry(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that analyser creates proper analysis chain entry.

        Business Logic: Each analyser must create a chain entry to track
        the analysis for audit purposes and downstream processing.
        """
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            llm_service=None,
        )

        # Act
        result = analyser.process(
            Schema("standard_input", "1.0.0"),
            Schema("personal_data_finding", "1.0.0"),
            sample_input_message,
        )

        # Assert
        analysis_metadata = result.content["analysis_metadata"]
        analyses_chain = analysis_metadata["analyses_chain"]

        assert len(analyses_chain) == 1, "Should create exactly one chain entry"

        chain_entry = analyses_chain[0]
        assert chain_entry["order"] == 1, "Should start with order 1 for new analysis"
        assert chain_entry["analyser"] == "personal_data_analyser", (
            "Should identify correct analyser"
        )
        assert "execution_timestamp" in chain_entry, (
            "Should include execution timestamp"
        )

    def test_reader_module_is_loaded_dynamically(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        mock_schema_modules: tuple[Mock, Mock],
    ) -> None:
        """Test that reader module is dynamically loaded for input schema."""
        # Arrange
        analyser = PersonalDataAnalyser(valid_config, mock_llm_service)
        mock_reader, mock_producer = mock_schema_modules

        # Mock importlib.import_module to track dynamic loading
        with patch("importlib.import_module") as mock_import:
            # Return different mocks based on module name
            def import_side_effect(module_name: str) -> Mock:
                if "schema_readers" in module_name:
                    return mock_reader
                elif "schema_producers" in module_name:
                    return mock_producer
                return Mock()

            mock_import.side_effect = import_side_effect

            input_schema = Schema("standard_input", "1.0.0")
            output_schema = Schema("personal_data_finding", "1.0.0")

            # Act
            analyser.process(input_schema, output_schema, sample_input_message)

            # Assert - Verify reader module was dynamically imported
            mock_import.assert_any_call(
                "waivern_personal_data_analyser.schema_readers.standard_input_1_0_0"
            )

    def test_producer_module_is_loaded_dynamically(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        mock_schema_modules: tuple[Mock, Mock],
    ) -> None:
        """Test that producer module is dynamically loaded for output schema."""
        # Arrange
        analyser = PersonalDataAnalyser(valid_config, mock_llm_service)
        mock_reader, mock_producer = mock_schema_modules

        # Mock importlib.import_module to track dynamic loading
        with patch("importlib.import_module") as mock_import:
            # Return different mocks based on module name
            def import_side_effect(module_name: str) -> Mock:
                if "schema_readers" in module_name:
                    return mock_reader
                elif "schema_producers" in module_name:
                    return mock_producer
                return Mock()

            mock_import.side_effect = import_side_effect

            input_schema = Schema("standard_input", "1.0.0")
            output_schema = Schema("personal_data_finding", "1.0.0")

            # Act
            analyser.process(input_schema, output_schema, sample_input_message)

            # Assert - Verify producer module was dynamically imported
            mock_import.assert_any_call(
                "waivern_personal_data_analyser.schema_producers.personal_data_finding_1_0_0"
            )
