"""Tests for processing purpose LLM validation strategy focusing on behavior."""

import json
from unittest.mock import Mock

import pytest

from wct.analysers.processing_purpose_analyser.llm_validation_strategy import (
    LLMValidationResultModel,
    processing_purpose_validation_strategy,
)
from wct.analysers.processing_purpose_analyser.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)
from wct.analysers.types import EvidenceItem, LLMValidationConfig
from wct.llm_service import AnthropicLLMService


class TestLLMValidationResultModel:
    """Test LLM validation result model."""

    def test_default_values(self) -> None:
        """Test that model has appropriate defaults."""
        result = LLMValidationResultModel()

        assert result.validation_result == "unknown"
        assert result.confidence == 0.0
        assert result.reasoning == "No reasoning provided"
        assert result.recommended_action == "keep"

    def test_validation_constraints(self) -> None:
        """Test model validation constraints."""
        # Valid confidence range
        valid_result = LLMValidationResultModel(confidence=0.85)
        assert valid_result.confidence == 0.85

        # Invalid confidence - too high
        with pytest.raises(ValueError):
            LLMValidationResultModel(confidence=1.5)

        # Invalid confidence - negative
        with pytest.raises(ValueError):
            LLMValidationResultModel(confidence=-0.1)


class TestProcessingPurposeValidationStrategy:
    """Test processing purpose validation strategy behavior."""

    def _create_test_finding(
        self,
        purpose: str = "Test Purpose",
        purpose_category: str = "OPERATIONAL",
        risk_level: str = "low",
        matched_pattern: str = "test",
        **kwargs,
    ) -> ProcessingPurposeFindingModel:
        """Helper to create test finding objects."""
        evidence = kwargs.get("evidence", [EvidenceItem(content="test evidence")])
        source = kwargs.get("source", "test_source")

        metadata = ProcessingPurposeFindingMetadata(source=source) if source else None

        return ProcessingPurposeFindingModel(
            purpose=purpose,
            purpose_category=purpose_category,
            risk_level=risk_level,
            matched_pattern=matched_pattern,
            evidence=evidence,
            metadata=metadata,
        )

    def test_empty_findings_returns_empty_list(self) -> None:
        """Test that empty findings list returns empty list."""
        config = LLMValidationConfig()
        mock_llm_service = Mock(spec=AnthropicLLMService)

        result, success = processing_purpose_validation_strategy(
            [], config, mock_llm_service
        )

        assert result == []
        assert success is True

    def test_filters_false_positives(self) -> None:
        """Test that false positive findings are filtered out."""
        findings = [
            self._create_test_finding(purpose="Documentation Example"),
            self._create_test_finding(purpose="Customer Service"),
        ]
        config = LLMValidationConfig()
        mock_llm_service = Mock(spec=AnthropicLLMService)

        # Mock LLM response indicating first is false positive, second is true positive
        mock_llm_service.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Documentation example",
                    "recommended_action": "discard",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.85,
                    "reasoning": "Actual business processing",
                    "recommended_action": "keep",
                },
            ]
        )

        result, success = processing_purpose_validation_strategy(
            findings, config, mock_llm_service
        )

        # Should keep only the true positive
        assert len(result) == 1
        assert result[0].purpose == "Customer Service"
        assert success is True

    def test_keeps_all_true_positives(self) -> None:
        """Test that all true positive findings are kept."""
        findings = [
            self._create_test_finding(purpose="Customer Support"),
            self._create_test_finding(purpose="Order Processing"),
        ]
        config = LLMValidationConfig()
        mock_llm_service = Mock(spec=AnthropicLLMService)

        # Mock LLM response indicating both are true positives
        mock_llm_service.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.88,
                    "reasoning": "Real customer support activity",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.92,
                    "reasoning": "Actual order processing",
                    "recommended_action": "keep",
                },
            ]
        )

        result, success = processing_purpose_validation_strategy(
            findings, config, mock_llm_service
        )

        # Should keep both findings
        assert len(result) == 2
        purposes = [finding.purpose for finding in result]
        assert "Customer Support" in purposes
        assert "Order Processing" in purposes
        assert success is True

    def test_error_handling_returns_original_findings(self) -> None:
        """Test that LLM errors return original findings safely."""
        findings = [self._create_test_finding(purpose="Test Purpose")]
        config = LLMValidationConfig()
        mock_llm_service = Mock(spec=AnthropicLLMService)

        # Mock LLM service to raise an exception
        mock_llm_service.analyse_data.side_effect = Exception("LLM service error")

        result, success = processing_purpose_validation_strategy(
            findings, config, mock_llm_service
        )

        # Should return original findings on error
        assert len(result) == 1
        assert result[0].purpose == "Test Purpose"
        assert success is False

    def test_handles_malformed_json_response(self) -> None:
        """Test graceful handling of malformed JSON responses."""
        findings = [self._create_test_finding(purpose="Test Purpose")]
        config = LLMValidationConfig()
        mock_llm_service = Mock(spec=AnthropicLLMService)

        # Mock invalid JSON response
        mock_llm_service.analyse_data.return_value = "invalid json response"

        result, success = processing_purpose_validation_strategy(
            findings, config, mock_llm_service
        )

        # Should return original findings on JSON parse error
        assert len(result) == 1
        assert result[0].purpose == "Test Purpose"
        assert success is False

    def test_handles_flag_for_review_action(self) -> None:
        """Test that flag_for_review action keeps findings."""
        findings = [self._create_test_finding(purpose="High Risk Processing")]
        config = LLMValidationConfig(llm_validation_mode="conservative")
        mock_llm_service = Mock(spec=AnthropicLLMService)

        # Mock response with flag_for_review action
        mock_llm_service.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.7,
                    "reasoning": "Requires manual review",
                    "recommended_action": "flag_for_review",
                }
            ]
        )

        result, success = processing_purpose_validation_strategy(
            findings, config, mock_llm_service
        )

        # Should keep findings marked for review
        assert len(result) == 1
        assert result[0].purpose == "High Risk Processing"
        assert success is True
