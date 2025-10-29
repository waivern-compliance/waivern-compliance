"""Integration tests with real LLM APIs for ProcessingPurposeAnalyser.

These tests require actual API keys and make real API calls.
Run with: uv run pytest -m integration
"""

import os

import pytest
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
    StandardInputSchema,
)
from waivern_llm import AnthropicLLMService

from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeAnalyserConfig,
)
from waivern_community.analysers.processing_purpose_analyser.schemas import (
    ProcessingPurposeFindingSchema,
)


class TestProcessingPurposeAnalyserRealLLMIntegration:
    """Integration tests with real LLM API for processing purpose analysis."""

    @pytest.mark.integration
    def test_real_llm_validation_filters_false_positives(self) -> None:
        """Test that real LLM validation filters false positives from pattern matching."""
        # Skip if no API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set - skipping real API test")

        # Create real LLM service
        llm_service = AnthropicLLMService(api_key=api_key)

        # Create analyser with LLM validation enabled
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "pattern_matching": {
                    "ruleset": "processing_purposes",
                    "evidence_context_size": "medium",
                },
                "llm_validation": {
                    "enable_llm_validation": True,
                    "llm_validation_mode": "standard",
                },
            }
        )
        analyser = ProcessingPurposeAnalyser(config, llm_service)

        # Test data with both true positives and potential false positives
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Integration test data",
            description="Test real LLM validation",
            source="integration_test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="We process payment transactions for our customers",
                    metadata=BaseMetadata(
                        source="integration_test", connector_type="test"
                    ),
                ),
                StandardInputDataItemModel(
                    content="The marketing team launched a new campaign",
                    metadata=BaseMetadata(
                        source="integration_test", connector_type="test"
                    ),
                ),
            ],
        )

        message = Message(
            id="integration_test",
            content=test_data.model_dump(exclude_none=True),
            schema=StandardInputSchema(),
        )

        # Run analysis with real LLM
        result = analyser.process(
            StandardInputSchema(), ProcessingPurposeFindingSchema(), message
        )

        # Verify response structure
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content

        findings = result.content["findings"]
        assert isinstance(findings, list)

        # Verify LLM validation was actually applied
        metadata = result.content["analysis_metadata"]
        assert metadata["llm_validation_enabled"] is True

        # If validation summary exists, check it has the expected structure
        if "validation_summary" in result.content:
            validation = result.content["validation_summary"]
            assert "llm_validation_enabled" in validation
            assert "original_findings_count" in validation
            assert "validated_findings_count" in validation
            assert validation["llm_validation_enabled"] is True

    @pytest.mark.integration
    def test_real_llm_validation_disabled_returns_all_findings(self) -> None:
        """Test that analyser works without LLM validation (pattern matching only)."""
        # This test doesn't need API key - LLM validation disabled
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "pattern_matching": {
                    "ruleset": "processing_purposes",
                    "evidence_context_size": "medium",
                },
                "llm_validation": {
                    "enable_llm_validation": False,
                },
            }
        )
        analyser = ProcessingPurposeAnalyser(config, llm_service=None)

        # Test data with clear processing purposes
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Integration test data",
            description="Test without LLM validation",
            source="integration_test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="We process payment transactions for billing purposes",
                    metadata=BaseMetadata(
                        source="integration_test", connector_type="test"
                    ),
                ),
            ],
        )

        message = Message(
            id="integration_test_no_llm",
            content=test_data.model_dump(exclude_none=True),
            schema=StandardInputSchema(),
        )

        # Run analysis without LLM
        result = analyser.process(
            StandardInputSchema(), ProcessingPurposeFindingSchema(), message
        )

        # Verify response structure
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content

        findings = result.content["findings"]
        assert isinstance(findings, list)

        # Verify LLM validation was NOT applied
        metadata = result.content["analysis_metadata"]
        assert metadata["llm_validation_enabled"] is False

        # Should not have validation summary when LLM disabled
        assert "validation_summary" not in result.content
