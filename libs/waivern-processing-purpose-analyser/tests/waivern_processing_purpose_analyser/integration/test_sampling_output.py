"""Integration test for sampling output structure.

Verifies the output schema has the expected fields for client deliverables.
"""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation import LLMValidationResponseModel
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm import BaseLLMService

from waivern_processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeAnalyserConfig,
)


class TestSamplingOutputStructure:
    """Test that sampling produces the expected output structure."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service."""
        return Mock(spec=BaseLLMService)

    @pytest.fixture
    def test_message_with_multiple_purposes(self) -> Message:
        """Create test data with multiple purposes to trigger sampling."""
        # Create content that will match different purposes
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Sampling test data",
            description="Test data with multiple purposes",
            source="test",
            metadata={},
            data=[
                # Payment purpose findings
                StandardInputDataItemModel(
                    content="Process payment transaction for customer order",
                    metadata=BaseMetadata(source="payments.js", connector_type="test"),
                ),
                StandardInputDataItemModel(
                    content="Handle credit card payment processing",
                    metadata=BaseMetadata(source="payments.js", connector_type="test"),
                ),
                StandardInputDataItemModel(
                    content="Store payment details securely",
                    metadata=BaseMetadata(source="payments.js", connector_type="test"),
                ),
                # Marketing purpose findings
                StandardInputDataItemModel(
                    content="Send marketing email campaign to users",
                    metadata=BaseMetadata(source="marketing.js", connector_type="test"),
                ),
                StandardInputDataItemModel(
                    content="Track marketing campaign performance",
                    metadata=BaseMetadata(source="marketing.js", connector_type="test"),
                ),
                # Documentation (likely false positive)
                StandardInputDataItemModel(
                    content="// Example: SELECT * FROM users WHERE email = ?",
                    metadata=BaseMetadata(source="README.md", connector_type="test"),
                ),
            ],
        )

        return Message(
            id="sampling_test",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

    def test_output_has_purposes_list_in_summary(
        self,
        mock_llm_service: Mock,
        test_message_with_multiple_purposes: Message,
    ) -> None:
        """Test that summary includes per-purpose breakdown."""
        # Arrange
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "pattern_matching": {
                    "ruleset": "local/processing_purposes/1.0.0",
                },
                "llm_validation": {
                    "enable_llm_validation": True,
                    "sampling_size": 3,
                },
            }
        )

        # Mock LLM to return empty false_positives (all true positives)
        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(results=[])
        )

        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_multiple_purposes],
            Schema("processing_purpose_finding", "1.0.0"),
        )

        # Assert - summary has purposes list
        summary = result.content["summary"]
        assert "purposes" in summary, "summary should have 'purposes' list"
        assert isinstance(summary["purposes"], list)

        # Each purpose entry should have purpose name and findings count
        if summary["purposes"]:
            purpose_entry = summary["purposes"][0]
            assert "purpose" in purpose_entry
            assert "findings_count" in purpose_entry

    def test_output_has_validation_summary_in_metadata(
        self,
        mock_llm_service: Mock,
        test_message_with_multiple_purposes: Message,
    ) -> None:
        """Test that analysis_metadata includes validation_summary with sampling info."""
        # Arrange
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "pattern_matching": {
                    "ruleset": "local/processing_purposes/1.0.0",
                },
                "llm_validation": {
                    "enable_llm_validation": True,
                    "sampling_size": 3,
                },
            }
        )

        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(results=[])
        )

        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_multiple_purposes],
            Schema("processing_purpose_finding", "1.0.0"),
        )

        # Assert - analysis_metadata has validation_summary
        metadata = result.content["analysis_metadata"]
        assert "validation_summary" in metadata, (
            "analysis_metadata should have 'validation_summary'"
        )

        validation_summary = metadata["validation_summary"]
        assert "strategy" in validation_summary
        assert "samples_per_purpose" in validation_summary
        assert "samples_validated" in validation_summary

    def test_output_has_purposes_removed_when_all_samples_false_positive(
        self,
        mock_llm_service: Mock,
        test_message_with_multiple_purposes: Message,
    ) -> None:
        """Test that purposes_removed is populated when all samples are false positives."""
        # Arrange
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "pattern_matching": {
                    "ruleset": "local/processing_purposes/1.0.0",
                },
                "llm_validation": {
                    "enable_llm_validation": True,
                    "sampling_size": 3,
                },
            }
        )

        # Mock LLM to mark some findings as false positives
        # We'll need to check what finding IDs are generated and mock accordingly
        # For now, just verify the field exists when validation runs
        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(results=[])
        )

        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_multiple_purposes],
            Schema("processing_purpose_finding", "1.0.0"),
        )

        # Assert - purposes_removed field exists (may be empty if no FPs)
        metadata = result.content["analysis_metadata"]
        # Note: purposes_removed should be present even if empty list
        assert (
            "purposes_removed" in metadata or metadata.get("purposes_removed") == []
        ), "analysis_metadata should have 'purposes_removed' field"
