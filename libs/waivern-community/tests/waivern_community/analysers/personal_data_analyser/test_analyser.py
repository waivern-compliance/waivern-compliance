"""Unit tests for PersonalDataAnalyser.

This test module focuses on testing the public API of PersonalDataAnalyser,
following black-box testing principles and proper encapsulation.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest
from waivern_core import Analyser
from waivern_core.message import Message, MessageValidationError
from waivern_core.schemas import (
    BaseFindingCompliance,
    BaseFindingEvidence,
    StandardInputSchema,
)
from waivern_core.schemas.base import SchemaLoadError

from waivern_community.analysers.personal_data_analyser.analyser import (
    PersonalDataAnalyser,
)
from waivern_community.analysers.personal_data_analyser.pattern_matcher import (
    PersonalDataPatternMatcher,
)
from waivern_community.analysers.personal_data_analyser.schemas import (
    PersonalDataFindingSchema,
)
from waivern_community.analysers.personal_data_analyser.types import (
    PersonalDataAnalyserConfig,
    PersonalDataFindingMetadata,
    PersonalDataFindingModel,
)
from waivern_community.analysers.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_community.analysers.utilities import LLMServiceManager
from waivern_community.connectors.source_code.schemas import SourceCodeSchema
from waivern_community.rulesets.personal_data import PersonalDataRule
from waivern_community.rulesets.types import RuleComplianceData


class TestPersonalDataAnalyser:
    """Test suite for PersonalDataAnalyser."""

    # Test constants - defined locally, not imported from implementation
    EXPECTED_ANALYSER_NAME = "personal_data_analyser"
    EXPECTED_OUTPUT_MESSAGE_ID = "Personal_data_analysis"
    HIGH_RISK_LEVEL = "high"
    MEDIUM_RISK_LEVEL = "medium"
    LOW_RISK_LEVEL = "low"

    @pytest.fixture
    def mock_pattern_matcher(self) -> Mock:
        """Create a mock pattern matcher."""
        return Mock(spec=PersonalDataPatternMatcher)

    @pytest.fixture
    def mock_llm_service_manager(self) -> Mock:
        """Create a mock LLM service manager."""
        return Mock(spec=LLMServiceManager)

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
            schema=StandardInputSchema(),
        )

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

    def test_from_properties_creates_analyser_with_valid_configuration(self) -> None:
        """Test creating analyser from properties dictionary."""
        # Arrange
        properties = {
            "pattern_matching": {
                "ruleset": "personal_data",
                "evidence_context_size": "small",
                "maximum_evidence_count": 3,
            },
            "llm_validation": {
                "enable_llm_validation": False,
                "llm_batch_size": 20,
                "llm_validation_mode": "conservative",
            },
        }

        # Act
        analyser = PersonalDataAnalyser.from_properties(properties)

        # Assert
        assert isinstance(analyser, PersonalDataAnalyser)
        # Test passes if no exception is raised

    def test_from_properties_raises_error_with_invalid_configuration(self) -> None:
        """Test that from_properties raises ValueError with invalid configuration."""
        # Arrange
        invalid_properties = {
            "pattern_matching": {
                "evidence_context_size": "invalid_size",  # Invalid value
            }
        }

        # Act & Assert
        with pytest.raises(
            ValueError, match="Invalid configuration for PersonalDataAnalyser"
        ):
            PersonalDataAnalyser.from_properties(invalid_properties)

    def test_from_properties_creates_analyser_with_default_values(self) -> None:
        """Test creating analyser with minimal properties uses defaults.

        This demonstrates the from_properties pattern with empty configuration.
        """
        # Arrange
        minimal_properties: dict[str, Any] = {}

        # Act
        analyser = PersonalDataAnalyser.from_properties(minimal_properties)

        # Assert
        assert isinstance(analyser, PersonalDataAnalyser)
        # Verify default values are applied
        # Test passes if no exception is raised

    def test_process_returns_valid_output_message_with_findings(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that process returns valid output message with minimal required findings structure."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_matcher, mock_llm_service_manager
        )

        # Mock pattern matcher to return findings for each data item
        mock_pattern_matcher.find_patterns.side_effect = [
            [sample_findings[0], sample_findings[1]],  # First data item
            [sample_findings[2]],  # Second data item
        ]

        # Mock LLM service manager
        mock_llm_service_manager.llm_service = Mock()
        with patch(
            "waivern_community.analysers.personal_data_analyser.analyser.personal_data_validation_strategy",
            return_value=(sample_findings, True),
        ):
            input_schema = StandardInputSchema()
            output_schema = PersonalDataFindingSchema()

            # Act
            result_message = analyser.process(
                input_schema, output_schema, sample_input_message
            )

            # Assert - Basic message structure
            assert isinstance(result_message, Message)
            assert result_message.id == self.EXPECTED_OUTPUT_MESSAGE_ID
            assert result_message.schema == output_schema

            # Verify findings structure
            result_content = result_message.content
            assert "findings" in result_content
            assert "summary" in result_content
            assert len(result_content["findings"]) == 3

            # Verify summary statistics
            summary = result_content["summary"]
            assert summary["total_findings"] == 3
            assert summary["high_risk_count"] == 1  # One high risk finding
            assert (
                summary["special_category_count"] == 0
            )  # No special category findings

    def test_process_findings_include_expected_metadata_and_categorical_info(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that findings include source metadata and data_type categorical information."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_matcher, mock_llm_service_manager
        )

        mock_pattern_matcher.find_patterns.side_effect = [
            [sample_findings[0], sample_findings[1]],
            [sample_findings[2]],
        ]

        mock_llm_service_manager.llm_service = Mock()
        with patch(
            "waivern_community.analysers.personal_data_analyser.analyser.personal_data_validation_strategy",
            return_value=(sample_findings, True),
        ):
            input_schema = StandardInputSchema()
            output_schema = PersonalDataFindingSchema()

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
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that personal data analyser provides standardised analysis metadata.

        Business Logic: All analysers must provide consistent metadata for
        downstream processing and analysis chaining capabilities.
        """
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_matcher, mock_llm_service_manager
        )

        mock_pattern_matcher.find_patterns.return_value = sample_findings
        mock_llm_service_manager.llm_service = None  # Disable LLM validation

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

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
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that validation summary is included when LLM validation is enabled."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_matcher, mock_llm_service_manager
        )

        # Mock pattern matcher to return specific findings for each data item
        mock_pattern_matcher.find_patterns.side_effect = [
            [sample_findings[0]],  # First data item returns one finding
            [sample_findings[1]],  # Second data item returns one finding
        ]

        # Mock LLM service manager
        mock_llm_service_manager.llm_service = Mock()
        filtered_findings = [sample_findings[0]]  # Remove one finding
        with patch(
            "waivern_community.analysers.personal_data_analyser.analyser.personal_data_validation_strategy",
            return_value=(filtered_findings, True),
        ):
            input_schema = StandardInputSchema()
            output_schema = PersonalDataFindingSchema()

            # Act
            result_message = analyser.process(
                input_schema, output_schema, sample_input_message
            )

            # Assert
            result_content = result_message.content
            assert "validation_summary" in result_content

            validation_summary = result_content["validation_summary"]
            assert validation_summary["llm_validation_enabled"] is True
            assert validation_summary["original_findings_count"] == 2
            assert validation_summary["validated_findings_count"] == 1
            assert validation_summary["false_positives_removed"] == 1
            assert validation_summary["validation_mode"] == "standard"

    def test_process_excludes_validation_summary_when_llm_validation_disabled(
        self,
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
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
            config_with_llm_disabled, mock_pattern_matcher, mock_llm_service_manager
        )

        mock_pattern_matcher.find_patterns.return_value = sample_findings
        mock_llm_service_manager.llm_service = None

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

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
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that validation summary is excluded when no findings are present."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_matcher, mock_llm_service_manager
        )

        # Mock pattern matcher to return no findings
        mock_pattern_matcher.find_patterns.return_value = []
        mock_llm_service_manager.llm_service = Mock()

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        result_message = analyser.process(
            input_schema, output_schema, sample_input_message
        )

        # Assert
        result_content = result_message.content
        assert "validation_summary" not in result_content
        assert result_content["summary"]["total_findings"] == 0

    def test_process_handles_empty_data_gracefully(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
    ) -> None:
        """Test that process handles empty input data gracefully."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_matcher, mock_llm_service_manager
        )

        empty_input_data: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "name": "Empty test data",
            "data": [],
        }
        empty_message = Message(
            id="empty_test",
            content=empty_input_data,
            schema=StandardInputSchema(),
        )

        # Mock pattern matcher to not be called for empty data
        mock_pattern_matcher.find_patterns.return_value = []
        mock_llm_service_manager.llm_service = Mock()

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        result_message = analyser.process(input_schema, output_schema, empty_message)

        # Assert
        assert isinstance(result_message, Message)
        result_content = result_message.content
        assert result_content["findings"] == []
        assert result_content["summary"]["total_findings"] == 0
        assert result_content["summary"]["high_risk_count"] == 0
        assert result_content["summary"]["special_category_count"] == 0

        # Verify pattern matcher was not called (no data items)
        mock_pattern_matcher.find_patterns.assert_not_called()

    def test_process_raises_error_with_invalid_schema(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
    ) -> None:
        """Test that process raises error when message schema doesn't match expected."""

        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_matcher, mock_llm_service_manager
        )

        # Create message with wrong schema
        wrong_message = Message(
            id="test_wrong_schema",
            content={"some": "data"},
            schema=SourceCodeSchema(),  # Wrong schema - expected StandardInputSchema
        )

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

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
            schema=StandardInputSchema(),
        )
        expected_schema = StandardInputSchema()

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
        expected_schema = StandardInputSchema()

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
            schema=StandardInputSchema(),
        )
        expected_schema = StandardInputSchema()

        # Act & Assert - should not raise any exception
        Analyser.validate_input_message(message, expected_schema)

    def test_validate_input_message_raises_error_with_invalid_message_content(
        self,
    ) -> None:
        """Test that validate_input_message raises error when message content is invalid."""
        # Arrange - create message with invalid content (missing required fields)
        invalid_content = {
            "schemaVersion": "1.0.0",
            # Missing required 'name' field
            "data": [],
        }
        message = Message(
            id="test_message",
            content=invalid_content,
            schema=StandardInputSchema(),
        )
        expected_schema = StandardInputSchema()

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
            schema=StandardInputSchema(),
        )
        expected_schema = StandardInputSchema()

        # Act & Assert - should raise MessageValidationError
        with pytest.raises(MessageValidationError, match="Schema validation failed"):
            Analyser.validate_input_message(message, expected_schema)

    def test_personal_data_finding_data_type_matches_rule_data_type(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service_manager: Mock,
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
                valid_config, pattern_matcher, mock_llm_service_manager
            )
            mock_llm_service_manager.llm_service = None  # Disable LLM validation

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
                id="test_data_type", content=input_content, schema=StandardInputSchema()
            )

            input_schema = StandardInputSchema()
            output_schema = PersonalDataFindingSchema()

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
        mock_pattern_matcher: Mock,
        mock_llm_service_manager: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that analyser creates proper analysis chain entry.

        Business Logic: Each analyser must create a chain entry to track
        the analysis for audit purposes and downstream processing.
        """
        # Arrange
        mock_pattern_matcher.find_patterns.return_value = []
        mock_llm_service_manager.llm_service = None

        analyser = PersonalDataAnalyser(
            config=valid_config,
            pattern_matcher=mock_pattern_matcher,
            llm_service_manager=mock_llm_service_manager,
        )

        # Act
        result = analyser.process(
            StandardInputSchema(),
            PersonalDataFindingSchema(),
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
