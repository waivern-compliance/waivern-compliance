"""Unit tests for PersonalDataAnalyser.

This test module focuses on testing the public API of PersonalDataAnalyser,
following black-box testing principles and proper encapsulation.
"""

from typing import Any, cast
from unittest.mock import Mock, patch

import pytest

from wct.analysers.personal_data_analyser.analyser import PersonalDataAnalyser
from wct.analysers.personal_data_analyser.types import (
    PersonalDataAnalyserConfig,
    PersonalDataFindingMetadata,
    PersonalDataFindingModel,
)
from wct.analysers.runners import LLMAnalysisRunner, PatternMatchingAnalysisRunner
from wct.analysers.runners.types import LLMValidationConfig, PatternMatchingConfig
from wct.message import Message
from wct.schemas import (
    PersonalDataFindingSchema,
    StandardInputDataItemMetadataModel,
    StandardInputSchema,
)


class TestPersonalDataAnalyser:
    """Test suite for PersonalDataAnalyser."""

    # Test constants - defined locally, not imported from implementation
    EXPECTED_ANALYSER_NAME = "personal_data_analyser"
    EXPECTED_OUTPUT_MESSAGE_ID = "Personal data analysis"
    HIGH_RISK_LEVEL = "high"
    MEDIUM_RISK_LEVEL = "medium"
    LOW_RISK_LEVEL = "low"
    SPECIAL_CATEGORY_YES = "Y"
    SPECIAL_CATEGORY_NO = "N"

    @pytest.fixture
    def mock_pattern_runner(self) -> Mock:
        """Create a mock pattern matching runner."""
        return Mock(spec=PatternMatchingAnalysisRunner)

    @pytest.fixture
    def mock_llm_runner(self) -> Mock:
        """Create a mock LLM analysis runner."""
        return Mock(spec=LLMAnalysisRunner)

    @pytest.fixture
    def valid_config(self) -> PersonalDataAnalyserConfig:
        """Create a valid configuration for testing."""
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
                    "metadata": {"source": "contact_form.html"},
                },
                {
                    "content": "User profile: john.doe@company.com, phone: +44-20-1234-5678",
                    "metadata": {"source": "user_database", "table": "users"},
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
                risk_level=self.MEDIUM_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_NO,
                matched_pattern="support@example.com",
                evidence=["Contact us at support@example.com"],
                metadata=PersonalDataFindingMetadata(source="contact_form.html"),
            ),
            PersonalDataFindingModel(
                type="phone",
                risk_level=self.HIGH_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_NO,
                matched_pattern="123-456-7890",
                evidence=["call 123-456-7890"],
                metadata=PersonalDataFindingMetadata(source="contact_form.html"),
            ),
            PersonalDataFindingModel(
                type="email",
                risk_level=self.MEDIUM_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_NO,
                matched_pattern="john.doe@company.com",
                evidence=["john.doe@company.com"],
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
        assert analyser.config.pattern_matching.ruleset == "personal_data"
        assert analyser.config.pattern_matching.evidence_context_size == "small"
        assert analyser.config.pattern_matching.maximum_evidence_count == 3
        assert analyser.config.llm_validation.enable_llm_validation is False
        assert analyser.config.llm_validation.llm_batch_size == 20
        assert analyser.config.llm_validation.llm_validation_mode == "conservative"

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
        """Test creating analyser with minimal properties uses defaults."""
        # Arrange
        minimal_properties: dict[str, Any] = {}

        # Act
        analyser = PersonalDataAnalyser.from_properties(minimal_properties)

        # Assert
        assert isinstance(analyser, PersonalDataAnalyser)
        # Verify default values are applied
        assert analyser.config.pattern_matching.ruleset == "personal_data"
        assert analyser.config.pattern_matching.evidence_context_size == "small"
        assert analyser.config.llm_validation.enable_llm_validation is True

    def test_process_returns_valid_output_message_with_findings(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that process returns a valid output message with findings."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        # Mock pattern runner to return findings for each data item
        mock_pattern_runner.run_analysis.side_effect = [
            [sample_findings[0], sample_findings[1]],  # First data item
            [sample_findings[2]],  # Second data item
        ]

        # Mock LLM runner to return all findings (no filtering)
        mock_llm_runner.run_analysis.return_value = sample_findings

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        result_message = analyser.process(
            input_schema, output_schema, sample_input_message
        )

        # Assert
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
        assert summary["special_category_count"] == 0  # No special category findings

    def test_process_includes_validation_summary_when_llm_validation_enabled(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that validation summary is included when LLM validation is enabled."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        # Mock pattern runner to return specific findings for each data item
        mock_pattern_runner.run_analysis.side_effect = [
            [sample_findings[0]],  # First data item returns one finding
            [sample_findings[1]],  # Second data item returns one finding
        ]

        # Mock LLM runner to filter out one finding (simulate false positive removal)
        filtered_findings = [sample_findings[0]]  # Remove one finding
        mock_llm_runner.run_analysis.return_value = filtered_findings

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
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that validation summary is excluded when LLM validation is disabled."""
        # Arrange
        config_with_llm_disabled = PersonalDataAnalyserConfig(
            pattern_matching=PatternMatchingConfig(),
            llm_validation=LLMValidationConfig(enable_llm_validation=False),
        )
        analyser = PersonalDataAnalyser(
            config_with_llm_disabled, mock_pattern_runner, mock_llm_runner
        )

        mock_pattern_runner.run_analysis.return_value = sample_findings
        mock_llm_runner.run_analysis.return_value = sample_findings

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
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that validation summary is excluded when no findings are present."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        # Mock runners to return no findings
        mock_pattern_runner.run_analysis.return_value = []
        mock_llm_runner.run_analysis.return_value = []

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
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
    ) -> None:
        """Test that process handles empty input data gracefully."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
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

        # Mock runners to return empty results
        mock_pattern_runner.run_analysis.return_value = []
        mock_llm_runner.run_analysis.return_value = []

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

        # Verify pattern runner was not called (no data items)
        mock_pattern_runner.run_analysis.assert_not_called()
        # LLM runner should still be called with empty findings list
        mock_llm_runner.run_analysis.assert_called_once()

    def test_process_correctly_counts_high_risk_findings(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that high risk findings are correctly counted in summary."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        high_risk_findings = [
            PersonalDataFindingModel(
                type="ssn",
                risk_level=self.HIGH_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_YES,
                matched_pattern="123-45-6789",
                evidence=["SSN: 123-45-6789"],
                metadata=PersonalDataFindingMetadata(source="test"),
            ),
            PersonalDataFindingModel(
                type="credit_card",
                risk_level=self.HIGH_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_NO,
                matched_pattern="4111-1111-1111-1111",
                evidence=["Card: 4111-1111-1111-1111"],
                metadata=PersonalDataFindingMetadata(source="test"),
            ),
            PersonalDataFindingModel(
                type="email",
                risk_level=self.LOW_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_NO,
                matched_pattern="test@example.com",
                evidence=["Email: test@example.com"],
                metadata=PersonalDataFindingMetadata(source="test"),
            ),
        ]

        mock_pattern_runner.run_analysis.return_value = high_risk_findings
        mock_llm_runner.run_analysis.return_value = high_risk_findings

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        result_message = analyser.process(
            input_schema, output_schema, sample_input_message
        )

        # Assert
        result_content = result_message.content
        summary = result_content["summary"]
        assert summary["total_findings"] == 3
        assert summary["high_risk_count"] == 2  # Two high risk findings
        assert summary["special_category_count"] == 1  # One special category finding

    def test_process_calls_runners_with_correct_parameters(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that process calls runners with the correct parameters."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        # Mock pattern runner to return specific findings for each data item
        mock_pattern_runner.run_analysis.side_effect = [
            [sample_findings[0]],  # First data item
            [sample_findings[1]],  # Second data item
        ]
        mock_llm_runner.run_analysis.return_value = sample_findings[:2]

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        analyser.process(input_schema, output_schema, sample_input_message)

        # Assert
        # Verify pattern runner was called for each data item
        assert mock_pattern_runner.run_analysis.call_count == 2

        # Verify LLM runner was called once with collected findings
        mock_llm_runner.run_analysis.assert_called_once()
        args = mock_llm_runner.run_analysis.call_args[0]
        assert len(args[0]) == 2  # Two findings collected from pattern runner
        assert args[2] == valid_config.llm_validation  # LLM config

    def test_process_passes_metadata_correctly_to_pattern_runner(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_findings: list[PersonalDataFindingModel],
    ) -> None:
        """Test that metadata is correctly passed to the pattern runner."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        test_input_data = {
            "schemaVersion": "1.0.0",
            "name": "Metadata test",
            "data": [
                {
                    "content": "Test content",
                    "metadata": {
                        "source": "test_file.txt",
                        "table": "users",
                        "extra_field": "extra_value",
                    },
                }
            ],
        }
        test_message = Message(
            id="metadata_test",
            content=test_input_data,
            schema=StandardInputSchema(),
        )

        mock_pattern_runner.run_analysis.return_value = sample_findings
        mock_llm_runner.run_analysis.return_value = sample_findings

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        analyser.process(input_schema, output_schema, test_message)

        # Assert
        # Verify pattern runner was called with correct metadata
        call_args = mock_pattern_runner.run_analysis.call_args[0]
        content = call_args[0]
        metadata = call_args[1]
        config = call_args[2]

        assert content == "Test content"
        assert isinstance(metadata, StandardInputDataItemMetadataModel)
        assert metadata.source == "test_file.txt"
        assert config == valid_config.pattern_matching

    @patch("wct.analysers.base.Analyser._validate_input_message")
    def test_process_validates_input_message(
        self,
        mock_validate: Mock,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that process validates the input message."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        mock_pattern_runner.run_analysis.return_value = []
        mock_llm_runner.run_analysis.return_value = []

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        analyser.process(input_schema, output_schema, sample_input_message)

        # Assert
        mock_validate.assert_called_once_with(sample_input_message, input_schema)

    def test_constructor_stores_configuration_and_runners(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
    ) -> None:
        """Test that constructor properly stores configuration and runners."""
        # Act
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        # Assert
        assert analyser.config == valid_config
        assert analyser.pattern_runner == mock_pattern_runner
        assert analyser.llm_runner == mock_llm_runner

    def test_process_returns_message_with_correct_structure(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that the output message has the expected structure."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        test_finding = PersonalDataFindingModel(
            type="email",
            risk_level=self.MEDIUM_RISK_LEVEL,
            special_category=self.SPECIAL_CATEGORY_NO,
            matched_pattern="test@example.com",
            evidence=["Contact: test@example.com"],
            metadata=PersonalDataFindingMetadata(source="test"),
        )

        mock_pattern_runner.run_analysis.return_value = [test_finding]
        mock_llm_runner.run_analysis.return_value = [test_finding]

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        result_message = analyser.process(
            input_schema, output_schema, sample_input_message
        )

        # Assert
        content = result_message.content

        # Verify required top-level keys
        assert "findings" in content
        assert "summary" in content

        # Verify findings structure
        findings_list = cast(list[dict[str, Any]], content["findings"])
        assert isinstance(findings_list, list)
        assert len(findings_list) == 1

        finding_dict = findings_list[0]
        assert "type" in finding_dict
        assert "risk_level" in finding_dict
        assert "special_category" in finding_dict
        assert "matched_pattern" in finding_dict
        assert "evidence" in finding_dict
        assert "metadata" in finding_dict

        # Verify summary structure
        summary = content["summary"]
        assert "total_findings" in summary
        assert "high_risk_count" in summary
        assert "special_category_count" in summary
        assert isinstance(summary["total_findings"], int)
        assert isinstance(summary["high_risk_count"], int)
        assert isinstance(summary["special_category_count"], int)

    def test_process_with_mixed_risk_levels_and_special_categories(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_pattern_runner: Mock,
        mock_llm_runner: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test processing with varied risk levels and special categories."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config, mock_pattern_runner, mock_llm_runner
        )

        mixed_findings = [
            PersonalDataFindingModel(
                type="health_data",
                risk_level=self.HIGH_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_YES,
                matched_pattern="patient diagnosis",
                evidence=["Medical condition: diabetes"],
                metadata=PersonalDataFindingMetadata(source="medical_record"),
            ),
            PersonalDataFindingModel(
                type="email",
                risk_level=self.LOW_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_NO,
                matched_pattern="public@company.com",
                evidence=["Contact: public@company.com"],
                metadata=PersonalDataFindingMetadata(source="website"),
            ),
            PersonalDataFindingModel(
                type="biometric",
                risk_level=self.HIGH_RISK_LEVEL,
                special_category=self.SPECIAL_CATEGORY_YES,
                matched_pattern="fingerprint scan",
                evidence=["Biometric auth: fingerprint"],
                metadata=PersonalDataFindingMetadata(source="security_system"),
            ),
        ]

        mock_pattern_runner.run_analysis.return_value = mixed_findings
        mock_llm_runner.run_analysis.return_value = mixed_findings

        input_schema = StandardInputSchema()
        output_schema = PersonalDataFindingSchema()

        # Act
        result_message = analyser.process(
            input_schema, output_schema, sample_input_message
        )

        # Assert
        content = result_message.content
        summary = content["summary"]

        assert summary["total_findings"] == 3
        assert summary["high_risk_count"] == 2  # health_data and biometric
        assert summary["special_category_count"] == 2  # health_data and biometric
