"""Tests for ProcessingPurposeAnalyser LLM validation behaviour - TDD approach.

These tests describe the expected behaviour of LLM validation integration
and should initially fail until the functionality is implemented.
"""

import json
from unittest.mock import Mock

import pytest
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
    StandardInputSchema,
)
from waivern_llm import BaseLLMService

from waivern_community.analysers.processing_purpose_analyser.analyser import (
    ProcessingPurposeAnalyser,
)
from waivern_community.analysers.processing_purpose_analyser.schemas import (
    ProcessingPurposeFindingSchema,
)
from waivern_community.analysers.processing_purpose_analyser.types import (
    ProcessingPurposeAnalyserConfig,
)


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
            schema=StandardInputSchema(),
        )

    def test_llm_validation_enabled_calls_llm_service_when_findings_exist(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM validation calls LLM service when findings exist and LLM is enabled."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        # Mock LLM response that keeps both findings
        mock_llm_service.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.8,
                    "reasoning": "Actual customer service processing",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Payment processing is legitimate",
                    "recommended_action": "keep",
                },
            ]
        )

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        analyser.process(
            StandardInputSchema(),
            ProcessingPurposeFindingSchema(),
            test_message_with_patterns,
        )

        # Assert - LLM service should be called for validation
        mock_llm_service.analyse_data.assert_called_once()

        # Verify the call was made with validation prompt
        call_args = mock_llm_service.analyse_data.call_args
        assert call_args[0][0] == ""  # empty prompt content
        assert "VALIDATION TASK" in call_args[0][1]  # validation prompt

    def test_llm_validation_filters_out_false_positives(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM validation filters out findings marked as false positives."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        # Mock LLM response that marks first finding as false positive
        mock_llm_service.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.95,
                    "reasoning": "Documentation example, not actual processing",
                    "recommended_action": "discard",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Actual payment processing",
                    "recommended_action": "keep",
                },
            ]
        )

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            StandardInputSchema(),
            ProcessingPurposeFindingSchema(),
            test_message_with_patterns,
        )

        # Assert - Should have fewer findings due to false positive filtering
        findings = result.content["findings"]
        validated_count = len(findings)

        # Should have validation summary showing reduction
        assert "validation_summary" in result.content
        validation_summary = result.content["validation_summary"]
        original_count = validation_summary["original_findings_count"]

        assert validated_count < original_count, (
            "LLM validation should filter false positives"
        )
        assert validation_summary["validated_findings_count"] == validated_count
        assert validation_summary["false_positives_removed"] == (
            original_count - validated_count
        )

        # Validate enhanced validation summary fields
        assert "validation_effectiveness_percentage" in validation_summary
        assert "validation_mode" in validation_summary
        assert "removed_purposes" in validation_summary

        assert isinstance(
            validation_summary["validation_effectiveness_percentage"], int | float
        )
        assert isinstance(validation_summary["validation_mode"], str)
        assert isinstance(validation_summary["removed_purposes"], list)

        # Validate effectiveness percentage calculation
        expected_effectiveness = (
            (original_count - validated_count) / original_count
        ) * 100
        assert validation_summary["validation_effectiveness_percentage"] == round(
            expected_effectiveness, 1
        )

        # Validate removed purposes logic
        for purpose in validation_summary["removed_purposes"]:
            assert isinstance(purpose, str)

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
            StandardInputSchema(),
            ProcessingPurposeFindingSchema(),
            test_message_with_patterns,
        )

        # Assert - LLM service should not be called
        mock_llm_service.analyse_data.assert_not_called()

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
            StandardInputSchema(),
            ProcessingPurposeFindingSchema(),
            test_message_with_patterns,
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
        mock_llm_service.analyse_data.side_effect = Exception("LLM service error")

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            StandardInputSchema(),
            ProcessingPurposeFindingSchema(),
            test_message_with_patterns,
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
            schema=StandardInputSchema(),
        )

        config = ProcessingPurposeAnalyserConfig.from_properties(properties)
        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            StandardInputSchema(),
            ProcessingPurposeFindingSchema(),
            test_message,
        )

        # Assert - LLM should not be called when no findings exist
        mock_llm_service.analyse_data.assert_not_called()

        # Should not have validation summary when no findings to validate
        assert "validation_summary" not in result.content
