"""Unit tests for PersonalDataAnalyser.

This test module focuses on testing the public API of PersonalDataAnalyser,
following black-box testing principles and proper encapsulation.
"""

import re
from typing import Any
from unittest.mock import Mock, patch

import pytest
from waivern_analysers_shared.llm_validation import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import BaseLLMService
from waivern_rulesets.personal_data_indicator import PersonalDataIndicatorRule

from waivern_personal_data_analyser.analyser import PersonalDataAnalyser
from waivern_personal_data_analyser.pattern_matcher import PersonalDataPatternMatcher
from waivern_personal_data_analyser.types import PersonalDataAnalyserConfig


def _extract_finding_ids_from_prompt(prompt: str) -> list[str]:
    """Extract finding IDs from the validation prompt."""
    pattern = r"\[([a-f0-9-]+)\]"
    return re.findall(pattern, prompt)


class TestPersonalDataAnalyser:
    """Test suite for PersonalDataAnalyser."""

    # Test constants - defined locally, not imported from implementation
    EXPECTED_ANALYSER_NAME = "personal_data_analyser"
    EXPECTED_OUTPUT_MESSAGE_ID_PREFIX = "personal_data_analysis_"

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create a mock LLM service with model_name for token estimation."""
        mock = Mock(spec=BaseLLMService)
        mock.model_name = "claude-3-5-sonnet"
        return mock

    @pytest.fixture
    def valid_config(self) -> PersonalDataAnalyserConfig:
        """Create a valid configuration for testing using direct instantiation."""
        return PersonalDataAnalyserConfig(
            pattern_matching=PatternMatchingConfig(
                ruleset="local/personal_data_indicator/1.0.0",
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
                    "content": "Contact email: support@example.com or phone: 123-456-7890",
                    "metadata": {
                        "source": "contact_form.html",
                        "connector_type": "filesystem",
                    },
                },
                {
                    "content": "User email: john.doe@company.com, phone: +44-20-1234-5678",
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
    def mock_reader_module(self) -> Mock:
        """Create mock reader module for testing dynamic loading.

        Returns:
            Mock reader module configured with appropriate return values.

        """
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
        return mock_reader

    def test_get_name_returns_correct_analyser_name(self) -> None:
        """Test that get_name returns the expected analyser name."""
        # Act
        name = PersonalDataAnalyser.get_name()

        # Assert
        assert name == self.EXPECTED_ANALYSER_NAME

    def test_get_input_requirements_returns_standard_input(self) -> None:
        """Test that the analyser declares standard_input as input requirement."""
        # Act
        requirements = PersonalDataAnalyser.get_input_requirements()

        # Assert
        assert len(requirements) == 1  # One valid combination
        assert len(requirements[0]) == 1  # One requirement in that combination
        assert requirements[0][0].schema_name == "standard_input"
        assert requirements[0][0].version == "1.0.0"

    def test_get_supported_output_schemas_returns_personal_data_indicator(self) -> None:
        """Test that the analyser outputs personal_data_indicator schema."""
        # Act
        output_schemas = PersonalDataAnalyser.get_supported_output_schemas()

        # Assert
        assert len(output_schemas) == 1
        assert output_schemas[0].name == "personal_data_indicator"
        assert output_schemas[0].version == "1.0.0"

    def test_process_returns_valid_output_message_with_findings(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that process returns valid output message with minimal required findings structure."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        # Mock LLM to keep all findings (return empty results = all TRUE_POSITIVE)
        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            return LLMValidationResponseModel(results=[])

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response
        output_schema = Schema("personal_data_indicator", "1.0.0")

        # Act
        result_message = analyser.process([sample_input_message], output_schema)

        # Assert - Basic message structure
        assert isinstance(result_message, Message)
        assert result_message.id.startswith(self.EXPECTED_OUTPUT_MESSAGE_ID_PREFIX)
        assert result_message.schema == output_schema

        # Verify findings structure exists (count may vary based on real pattern matching)
        result_content = result_message.content
        assert "findings" in result_content
        assert "summary" in result_content
        assert isinstance(result_content["findings"], list)

        # Verify summary statistics structure
        summary = result_content["summary"]
        assert "total_findings" in summary
        assert summary["total_findings"] == len(result_content["findings"])  # type: ignore[arg-type]

    def test_process_findings_include_expected_metadata_and_category(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that findings include source metadata and category information."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        # Mock LLM to keep all findings
        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            return LLMValidationResponseModel(results=[])

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response
        output_schema = Schema("personal_data_indicator", "1.0.0")

        # Act
        result_message = analyser.process([sample_input_message], output_schema)

        # Assert - Verify source field and category are included
        result_content = result_message.content
        for finding in result_content["findings"]:
            # Test source field directly
            assert finding["metadata"]["source"] in [
                "contact_form.html",
                "user_database",
            ]

            # Test category field (granular indicator category)
            assert "category" in finding, (
                "PersonalDataIndicatorModel should include category field"
            )
            assert isinstance(finding["category"], str)
            assert finding["category"] != "", "category should not be empty"

    def test_personal_data_analyser_provides_standardised_analysis_metadata(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
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

        # Mock LLM to keep all findings
        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            return LLMValidationResponseModel(results=[])

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response
        output_schema = Schema("personal_data_indicator", "1.0.0")

        # Act
        result_message = analyser.process([sample_input_message], output_schema)

        # Assert - Verify analysis_metadata exists and has core standardised fields
        result_content = result_message.content
        assert "analysis_metadata" in result_content, (
            "Personal data analyser must provide analysis_metadata for chaining support"
        )

        analysis_metadata = result_content["analysis_metadata"]

        # Core standardised fields required for analysis metadata
        assert "ruleset_used" in analysis_metadata
        assert "llm_validation_enabled" in analysis_metadata
        assert "evidence_context_size" in analysis_metadata

        # Verify field types and values match business requirements
        assert isinstance(analysis_metadata["ruleset_used"], str)
        assert isinstance(analysis_metadata["llm_validation_enabled"], bool)
        assert (
            analysis_metadata["ruleset_used"] == "local/personal_data_indicator/1.0.0"
        )

    def test_process_includes_validation_summary_when_llm_validation_enabled(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
    ) -> None:
        """Test that validation summary is included when LLM validation is enabled."""
        # Arrange
        analyser = PersonalDataAnalyser(
            valid_config,
            mock_llm_service,
        )

        # Mock LLM to mark first finding in prompt as FALSE_POSITIVE
        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            finding_ids = _extract_finding_ids_from_prompt(prompt)
            if finding_ids:
                # Mark first finding as false positive
                return LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=finding_ids[0],
                            validation_result="FALSE_POSITIVE",
                            confidence=0.9,
                            reasoning="Test false positive",
                            recommended_action="discard",
                        )
                    ]
                )
            return LLMValidationResponseModel(results=[])

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response
        output_schema = Schema("personal_data_indicator", "1.0.0")

        # Act
        result_message = analyser.process([sample_input_message], output_schema)

        # Assert - Verify validation summary in analysis_metadata
        result_content = result_message.content
        analysis_metadata = result_content["analysis_metadata"]

        # Validation summary is in analysis_metadata when using orchestrator
        if result_content["summary"]["total_findings"] >= 0:
            assert "validation_summary" in analysis_metadata
            validation_summary = analysis_metadata["validation_summary"]
            assert validation_summary["strategy"] == "orchestrated"
            assert "samples_validated" in validation_summary
            assert "all_succeeded" in validation_summary

    def test_process_excludes_validation_summary_when_llm_validation_disabled(
        self,
        sample_input_message: Message,
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

        output_schema = Schema("personal_data_indicator", "1.0.0")

        # Act
        result_message = analyser.process([sample_input_message], output_schema)

        # Assert
        result_content = result_message.content
        assert "validation_summary" not in result_content

    def test_process_excludes_validation_summary_when_no_findings(
        self,
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

        output_schema = Schema("personal_data_indicator", "1.0.0")

        # Act
        result_message = analyser.process([empty_message], output_schema)

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

        output_schema = Schema("personal_data_indicator", "1.0.0")

        # Act
        result_message = analyser.process([empty_message], output_schema)

        # Assert - Verify analyser handles empty data correctly
        assert isinstance(result_message, Message)
        result_content = result_message.content
        assert result_content["findings"] == []
        assert result_content["summary"]["total_findings"] == 0

    def test_personal_data_indicator_category_matches_rule_category(
        self,
        valid_config: PersonalDataAnalyserConfig,
    ) -> None:
        """Test that finding.category matches the rule.category it was processed against."""
        # Arrange
        # Create a mock rule with known category
        mock_rule = PersonalDataIndicatorRule(
            name="Email Address",
            description="Test rule for email detection",
            patterns=("email",),
            category="email",  # This should appear in finding.category
        )

        # Create real pattern matcher and mock its ruleset manager
        pattern_matcher = PersonalDataPatternMatcher(valid_config.pattern_matching)
        with patch.object(
            pattern_matcher._ruleset_manager,  # pyright: ignore[reportPrivateUsage]
            "get_rules",
            return_value=[mock_rule],
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
                id="test_category",
                content=input_content,
                schema=Schema("standard_input", "1.0.0"),
            )

            output_schema = Schema("personal_data_indicator", "1.0.0")

            # Act
            result_message = analyser.process([test_message], output_schema)

            # Assert - verify that finding.category matches rule.category
            result_content = result_message.content
            findings = result_content["findings"]
            assert len(findings) > 0, "Should have at least one finding"

            for finding in findings:
                assert finding["category"] == "email", (
                    f"Finding category should match rule.category, got: {finding.get('category')}"
                )

    def test_reader_module_is_loaded_dynamically(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        mock_reader_module: Mock,
    ) -> None:
        """Test that reader module is dynamically loaded for input schema."""
        # Arrange
        analyser = PersonalDataAnalyser(valid_config, mock_llm_service)

        # Mock importlib.import_module to track dynamic loading
        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = mock_reader_module

            output_schema = Schema("personal_data_indicator", "1.0.0")

            # Act
            analyser.process([sample_input_message], output_schema)

            # Assert - Verify reader module was dynamically imported
            mock_import.assert_any_call(
                "waivern_personal_data_analyser.schema_readers.standard_input_1_0_0"
            )

    def test_produces_findings_from_all_input_sources(self) -> None:
        """PersonalDataAnalyser produces findings from all provided input messages."""
        # Arrange
        config = PersonalDataAnalyserConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": False}}
        )
        analyser = PersonalDataAnalyser(config, llm_service=None)

        message1 = Message(
            id="mysql_data",
            content={
                "schemaVersion": "1.0.0",
                "name": "MySQL extraction",
                "data": [
                    {
                        "content": "User email: john.doe@company.com, phone: 123-456",
                        "metadata": {
                            "source": "users_table",
                            "connector_type": "mysql",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )
        message2 = Message(
            id="file_data",
            content={
                "schemaVersion": "1.0.0",
                "name": "File extraction",
                "data": [
                    {
                        "content": "Contact email: support@example.com",
                        "metadata": {
                            "source": "contact.html",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )
        output_schema = Schema("personal_data_indicator", "1.0.0")

        # Act
        result = analyser.process([message1, message2], output_schema)

        # Assert - Findings from both sources appear in output
        findings = result.content["findings"]
        sources = {f["metadata"]["source"] for f in findings}
        assert "users_table" in sources, "Should have findings from MySQL source"
        assert "contact.html" in sources, "Should have findings from file source"


class TestPersonalDataAnalyserContract(AnalyserContractTests[PersonalDataAnalyser]):
    """Contract tests for PersonalDataAnalyser.

    Inherits from AnalyserContractTests to verify that PersonalDataAnalyser
    meets the Analyser interface contract.
    """

    @pytest.fixture
    def processor_class(self) -> type[PersonalDataAnalyser]:
        """Provide the processor class for contract testing."""
        return PersonalDataAnalyser
