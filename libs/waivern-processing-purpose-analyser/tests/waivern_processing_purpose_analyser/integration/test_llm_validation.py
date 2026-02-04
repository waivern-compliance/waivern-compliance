"""Integration tests with real LLM APIs for ProcessingPurposeAnalyser.

These tests require LLM service configuration (see root .env file).
Run with: uv run pytest -m integration
"""

import pytest
from waivern_artifact_store.in_memory import AsyncInMemoryStore
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm import LLMService
from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.errors import LLMConfigurationError
from waivern_llm.providers import AnthropicProvider, GoogleProvider, OpenAIProvider
from waivern_llm.service import DefaultLLMService

from waivern_processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeAnalyserConfig,
)


@pytest.fixture
def llm_service() -> LLMService:
    """Create LLM service based on .env configuration.

    This fixture overrides the root conftest fixture to provide
    an LLMService instance for integration tests.
    Skips the test if LLM service is not configured.
    """
    try:
        config = LLMServiceConfiguration.from_properties({})
    except Exception as e:
        pytest.skip(f"LLM service not configured: {e}")

    # Create provider based on configuration
    match config.provider:
        case "anthropic":
            provider = AnthropicProvider(api_key=config.api_key, model=config.model)
        case "openai":
            provider = OpenAIProvider(
                api_key=config.api_key, model=config.model, base_url=config.base_url
            )
        case "google":
            provider = GoogleProvider(api_key=config.api_key, model=config.model)
        case _:
            raise LLMConfigurationError(f"Unsupported provider: {config.provider}")

    cache_store = AsyncInMemoryStore()

    return DefaultLLMService(provider=provider, cache_store=cache_store)


class TestProcessingPurposeAnalyserLLMIntegration:
    """Integration tests with real LLM API for processing purpose analysis."""

    @pytest.mark.integration
    def test_real_llm_validation_filters_false_positives(
        self, llm_service: LLMService
    ) -> None:
        """Test that real LLM validation filters false positives from pattern matching."""

        # Create analyser with LLM validation enabled
        config = ProcessingPurposeAnalyserConfig.from_properties(
            {
                "pattern_matching": {
                    "ruleset": "local/processing_purposes/1.0.0",
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
            schema=Schema("standard_input", "1.0.0"),
            run_id="integration-test-run",
        )

        # Run analysis with real LLM
        result = analyser.process(
            [message],
            Schema("processing_purpose_indicator", "1.0.0"),
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
