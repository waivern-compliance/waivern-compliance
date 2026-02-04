"""Integration test for sampling output structure.

Verifies the output schema has the expected fields for client deliverables.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
)
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm import LLMCompletionResult, LLMService

from waivern_processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeAnalyserConfig,
)


class TestSamplingOutputStructure:
    """Test that sampling produces the expected output structure."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service."""
        service = Mock(spec=LLMService)
        service.complete = AsyncMock()
        return service

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
            run_id="test-sampling-run",
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

        # Mock LLM to return empty results (all true positives)
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )

        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_multiple_purposes],
            Schema("processing_purpose_indicator", "1.0.0"),
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
        """Test that analysis_metadata includes validation_summary with orchestrator info."""
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

        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )

        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_multiple_purposes],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Assert - analysis_metadata has validation_summary with orchestrator fields
        metadata = result.content["analysis_metadata"]
        assert "validation_summary" in metadata, (
            "analysis_metadata should have 'validation_summary'"
        )

        validation_summary = metadata["validation_summary"]
        assert validation_summary["strategy"] == "orchestrated"
        assert "samples_validated" in validation_summary
        assert "all_succeeded" in validation_summary
        assert "skipped_count" in validation_summary

    def test_output_no_purposes_removed_when_no_false_positives(
        self,
        mock_llm_service: Mock,
        test_message_with_multiple_purposes: Message,
    ) -> None:
        """Test that purposes_removed is absent when no samples are false positives."""
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

        # Mock LLM to return empty results (all findings are true positives)
        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )

        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_multiple_purposes],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Assert - purposes_removed should NOT be present when no groups removed
        metadata = result.content["analysis_metadata"]
        assert "purposes_removed" not in metadata, (
            "purposes_removed should not be present when no groups are removed"
        )
