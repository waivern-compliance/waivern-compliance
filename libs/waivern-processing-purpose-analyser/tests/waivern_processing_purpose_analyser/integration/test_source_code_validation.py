"""Integration test for source_code schema LLM validation.

Verifies the SourceCodeValidationStrategy is exercised correctly when
processing source_code schema input with LLM validation enabled.
"""

import re
from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import BaseLLMService

from waivern_processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeAnalyserConfig,
)


def _extract_finding_ids_from_prompt(prompt: str) -> list[str]:
    """Extract finding IDs from the validation prompt."""
    pattern = r"\[([a-f0-9-]+)\]"
    return re.findall(pattern, prompt)


class TestSourceCodeSchemaLLMValidation:
    """Integration tests for source_code schema with LLM validation.

    These tests verify that the SourceCodeValidationStrategy is used
    and that file content is available in the validation prompt.
    """

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service with model_name for token estimation."""
        mock = Mock(spec=BaseLLMService)
        mock.model_name = "claude-3-5-sonnet"  # Required for token window lookup
        return mock

    @pytest.fixture
    def source_code_message(self) -> Message:
        """Create source_code schema message with processing purpose patterns."""
        content = {
            "schemaVersion": "1.0.0",
            "name": "Test PHP Analysis",
            "description": "Test source code for LLM validation",
            "language": "php",
            "source": "test_repo",
            "metadata": {
                "total_files": 1,
                "total_lines": 20,
                "analysis_timestamp": "2025-01-01T00:00:00Z",
            },
            "data": [
                {
                    "file_path": "/src/PaymentService.php",
                    "language": "php",
                    "raw_content": """<?php
class PaymentService {
    public function processPayment($amount) {
        // Process customer payment securely
        return $this->gateway->charge($amount);
    }

    public function refundTransaction($transactionId) {
        // Refund a previous transaction
        return $this->gateway->refund($transactionId);
    }
}
""",
                    "metadata": {
                        "file_size": 350,
                        "line_count": 12,
                        "last_modified": "2025-01-01T00:00:00Z",
                    },
                }
            ],
        }
        return Message(
            id="test_source_code",
            content=content,
            schema=Schema("source_code", "1.0.0"),
        )

    def test_source_code_validation_includes_file_content_in_prompt(
        self,
        mock_llm_service: Mock,
        source_code_message: Message,
    ) -> None:
        """Verify that source_code validation includes file content in the prompt.

        This confirms SourceCodeValidationStrategy is being used, which provides
        full file content for richer validation context.
        """
        # Arrange
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "llm_validation": {
                    "enable_llm_validation": True,
                },
            }
        )

        captured_prompt: str = ""

        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            nonlocal captured_prompt
            captured_prompt = prompt
            return LLMValidationResponseModel(results=[])

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response

        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        analyser.process(
            [source_code_message],
            Schema("processing_purpose_finding", "1.0.0"),
        )

        # Assert - prompt should contain file content (SourceCodeValidationStrategy)
        assert mock_llm_service.invoke_with_structured_output.called, (
            "LLM service should be called for validation"
        )
        assert "PaymentService.php" in captured_prompt, (
            "Prompt should include file path"
        )
        assert "processPayment" in captured_prompt, (
            "Prompt should include file content (method name)"
        )
        assert "refundTransaction" in captured_prompt, (
            "Prompt should include file content (method name)"
        )

    def test_source_code_validation_filters_false_positives(
        self,
        mock_llm_service: Mock,
        source_code_message: Message,
    ) -> None:
        """Verify that false positives are filtered from source_code findings."""
        # Arrange
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "llm_validation": {
                    "enable_llm_validation": True,
                },
            }
        )

        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            finding_ids = _extract_finding_ids_from_prompt(prompt)
            if not finding_ids:
                return LLMValidationResponseModel(results=[])
            # Mark first finding as false positive, keep rest
            results = [
                LLMValidationResultModel(
                    finding_id=finding_ids[0],
                    validation_result="FALSE_POSITIVE",
                    confidence=0.9,
                    reasoning="Comment only, not actual processing",
                    recommended_action="discard",
                )
            ]
            for fid in finding_ids[1:]:
                results.append(
                    LLMValidationResultModel(
                        finding_id=fid,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.85,
                        reasoning="Actual payment processing",
                        recommended_action="keep",
                    )
                )
            return LLMValidationResponseModel(results=results)

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response

        analyser = ProcessingPurposeAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [source_code_message],
            Schema("processing_purpose_finding", "1.0.0"),
        )

        # Assert - validation should have been applied
        metadata = result.content["analysis_metadata"]
        assert "validation_summary" in metadata, (
            "Should have validation_summary when LLM validation applied"
        )
        assert metadata["validation_summary"]["strategy"] == "orchestrated"

        # All remaining findings should be marked as validated
        for finding in result.content["findings"]:
            assert (
                finding.get("metadata", {})
                .get("context", {})
                .get("processing_purpose_llm_validated")
            ), "All findings should be marked as validated"
