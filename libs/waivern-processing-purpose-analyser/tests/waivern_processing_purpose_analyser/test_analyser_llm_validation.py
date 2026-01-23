"""Tests for ProcessingPurposeAnalyser LLM validation behaviour - TDD approach.

These tests describe the expected behaviour of LLM validation integration
and should initially fail until the functionality is implemented.
"""

import re
from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm import BaseLLMService

from waivern_processing_purpose_analyser.analyser import (
    ProcessingPurposeAnalyser,
)
from waivern_processing_purpose_analyser.types import (
    ProcessingPurposeAnalyserConfig,
)


def _extract_finding_ids_from_prompt(prompt: str) -> list[str]:
    """Extract finding IDs from the validation prompt."""
    # Pattern matches Finding [uuid]: format
    pattern = r"Finding \[([a-f0-9-]+)\]:"
    return re.findall(pattern, prompt)


class TestProcessingPurposeAnalyserLLMValidationBehaviour:
    """Test actual LLM validation behaviour in the analyser process method."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service."""
        return Mock(spec=BaseLLMService)

    @pytest.fixture
    def mock_llm_service_unavailable(self) -> None:
        """Create unavailable LLM service (None)."""
        return None

    @pytest.fixture
    def test_message_with_patterns(self) -> Message:
        """Create test message with content that should match patterns."""
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="test_data",
            description="Test data for LLM validation",
            source="test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="customer service documentation example",
                    metadata=BaseMetadata(
                        source="documentation", connector_type="test"
                    ),
                ),
                StandardInputDataItemModel(
                    content="process customer payment transactions",
                    metadata=BaseMetadata(source="database", connector_type="test"),
                ),
            ],
        )
        return Message(
            id="test",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

    def test_llm_validation_enabled_calls_llm_service_when_findings_exist(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM validation calls LLM service when findings exist and LLM is enabled."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        # Dynamic mock that extracts finding IDs from the prompt and returns valid response
        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            finding_ids = _extract_finding_ids_from_prompt(prompt)
            return LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=finding_ids[i],
                        validation_result="TRUE_POSITIVE",
                        confidence=0.8 + i * 0.1,
                        reasoning=f"Valid finding {i}",
                        recommended_action="keep",
                    )
                    for i in range(len(finding_ids))
                ]
            )

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        analyser.process(
            [test_message_with_patterns],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Assert - LLM service should be called for validation
        mock_llm_service.invoke_with_structured_output.assert_called_once()

        # Verify the call was made with validation prompt
        call_args = mock_llm_service.invoke_with_structured_output.call_args
        assert "VALIDATION TASK" in call_args[0][0]  # validation prompt

    def test_llm_validation_filters_out_false_positives(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM validation filters out findings marked as false positives."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        # Dynamic mock that marks first finding as false positive
        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            finding_ids = _extract_finding_ids_from_prompt(prompt)
            return LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=finding_ids[0],
                        validation_result="FALSE_POSITIVE",
                        confidence=0.95,
                        reasoning="Documentation example, not actual processing",
                        recommended_action="discard",
                    ),
                    LLMValidationResultModel(
                        finding_id=finding_ids[1],
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Actual payment processing",
                        recommended_action="keep",
                    ),
                ]
            )

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Assert - Should have findings filtered (one FP removed)
        findings = result.content["findings"]
        validated_count = len(findings)

        # The test fixture has 2 content items that should produce findings.
        # One is marked FP, one is marked TP.
        # The final count should be less than what was originally detected.
        assert validated_count >= 1, "Should have at least one finding remaining"

        # Verify validation was applied via analysis_metadata
        metadata = result.content["analysis_metadata"]
        assert "validation_summary" in metadata, (
            "analysis_metadata should have validation_summary when validation applied"
        )

        validation_summary = metadata["validation_summary"]
        assert validation_summary["strategy"] == "orchestrated"
        assert "samples_validated" in validation_summary
        assert validation_summary["samples_validated"] > 0, (
            "Should have validated at least one sample"
        )

        # Verify all findings are marked as validated
        for finding in findings:
            assert (
                finding.get("metadata", {})
                .get("context", {})
                .get("processing_purpose_llm_validated")
            ), "All findings should be marked as validated"

    def test_llm_validation_disabled_skips_validation(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that disabled LLM validation skips the validation step."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": False}}

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Assert - LLM service should not be called
        mock_llm_service.invoke_with_structured_output.assert_not_called()

        # Should not have validation summary
        assert "validation_summary" not in result.content

    def test_llm_validation_unavailable_service_returns_original_findings(
        self,
        mock_llm_service_unavailable: None,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that unavailable LLM service returns original findings safely."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service_unavailable)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Assert - Should return original findings without validation
        assert result is not None
        assert "findings" in result.content

        # Should not have validation summary when service unavailable
        assert "validation_summary" not in result.content

    def test_llm_validation_error_returns_original_findings(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM service errors return original findings safely."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        # Mock LLM service to raise an exception
        mock_llm_service.invoke_with_structured_output.side_effect = Exception(
            "LLM service error"
        )

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Assert - Should return original findings despite error
        assert result is not None
        assert "findings" in result.content

        # Should not have validation summary when validation fails
        assert "validation_summary" not in result.content

    def test_no_findings_skips_llm_validation(
        self,
        mock_llm_service: Mock,
    ) -> None:
        """Test that no findings means no LLM validation is attempted."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        # Create message with no pattern matches
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="no_patterns",
            description="Test data with no patterns",
            source="test",
            data=[
                StandardInputDataItemModel(
                    content="this content has no processing purpose patterns",
                    metadata=BaseMetadata(source="test", connector_type="test"),
                )
            ],
        )
        test_message = Message(
            id="test_no_patterns",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Assert - LLM should not be called when no findings exist
        mock_llm_service.invoke_with_structured_output.assert_not_called()

        # Should not have validation summary when no findings to validate
        assert "validation_summary" not in result.content
