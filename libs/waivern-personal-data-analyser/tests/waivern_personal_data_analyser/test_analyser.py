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
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseFindingEvidence,
    Schema,
)
from waivern_llm import BaseLLMService
from waivern_rulesets.personal_data import PersonalDataRule

from waivern_personal_data_analyser.analyser import (
    PersonalDataAnalyser,
)
from waivern_personal_data_analyser.pattern_matcher import (
    PersonalDataPatternMatcher,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataIndicatorMetadata,
    PersonalDataIndicatorModel,
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
                ruleset="local/personal_data/1.0.0",
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

    @pytest.fixture
    def sample_findings(self) -> list[PersonalDataIndicatorModel]:
        """Create sample personal data findings for testing.

        Note: matched_patterns contains keywords that the pattern matcher looks for
        (e.g., "email", "phone"), not the actual data values.
        """
        return [
            PersonalDataIndicatorModel(
                type="Basic Profile Information",
                data_type="basic_profile",
                matched_patterns=["email"],
                evidence=[
                    BaseFindingEvidence(content="Contact us at support@example.com")
                ],
                metadata=PersonalDataIndicatorMetadata(source="contact_form.html"),
            ),
            PersonalDataIndicatorModel(
                type="Basic Profile Information",
                data_type="basic_profile",
                matched_patterns=["telephone"],
                evidence=[BaseFindingEvidence(content="call 123-456-7890")],
                metadata=PersonalDataIndicatorMetadata(source="contact_form.html"),
            ),
            PersonalDataIndicatorModel(
                type="Basic Profile Information",
                data_type="basic_profile",
                matched_patterns=["email"],
                evidence=[
                    BaseFindingEvidence(content="User email: john.doe@company.com")
                ],
                metadata=PersonalDataIndicatorMetadata(source="user_database"),
            ),
        ]

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
        sample_findings: list[PersonalDataIndicatorModel],
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
            output_schema = Schema("personal_data_indicator", "1.0.0")

            # Act
            result_message = analyser.process([sample_input_message], output_schema)

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
            assert summary["total_findings"] == len(result_content["findings"])  # type: ignore[arg-type]

    def test_process_findings_include_expected_metadata_and_categorical_info(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataIndicatorModel],
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
            output_schema = Schema("personal_data_indicator", "1.0.0")

            # Act
            result_message = analyser.process([sample_input_message], output_schema)

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
                    "PersonalDataIndicatorModel should include data_type field for categorical reference"
                )
                assert isinstance(finding["data_type"], str)
                assert finding["data_type"] != "", "data_type should not be empty"

    def test_personal_data_analyser_provides_standardised_analysis_metadata(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataIndicatorModel],
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
            output_schema = Schema("personal_data_indicator", "1.0.0")

            # Act
            result_message = analyser.process([sample_input_message], output_schema)

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
        assert analysis_metadata["ruleset_used"] == "local/personal_data/1.0.0"

    def test_process_includes_validation_summary_when_llm_validation_enabled(
        self,
        valid_config: PersonalDataAnalyserConfig,
        mock_llm_service: Mock,
        sample_input_message: Message,
        sample_findings: list[PersonalDataIndicatorModel],
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
            output_schema = Schema("personal_data_indicator", "1.0.0")

            # Act
            result_message = analyser.process([sample_input_message], output_schema)

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

    def test_personal_data_indicator_data_type_matches_rule_data_type(
        self,
        valid_config: PersonalDataAnalyserConfig,
    ) -> None:
        """Test that finding.data_type matches the rule.data_type it was processed against."""
        # Arrange
        # Create a mock rule with known data_type
        mock_rule = PersonalDataRule(
            name="Test Email Detection",
            description="Test rule for email detection",
            patterns=("email",),
            data_type="basic_profile",  # This should appear in finding.data_type
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
                id="test_data_type",
                content=input_content,
                schema=Schema("standard_input", "1.0.0"),
            )

            output_schema = Schema("personal_data_indicator", "1.0.0")

            # Act
            result_message = analyser.process([test_message], output_schema)

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
            [sample_input_message],
            Schema("personal_data_indicator", "1.0.0"),
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
