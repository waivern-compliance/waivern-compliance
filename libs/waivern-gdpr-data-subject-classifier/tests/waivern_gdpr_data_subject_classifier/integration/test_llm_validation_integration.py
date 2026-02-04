"""Integration tests with real LLM APIs for GDPRDataSubjectClassifier.

These tests verify the LLM's semantic understanding capabilities for
risk modifier detection - something that cannot be tested with mocks.

Run with: uv run pytest -m integration
"""

import pytest
from waivern_artifact_store.in_memory import AsyncInMemoryStore
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.errors import LLMConfigurationError
from waivern_llm.v2 import LLMService
from waivern_llm.v2.providers import AnthropicProvider, GoogleProvider, OpenAIProvider
from waivern_llm.v2.service import DefaultLLMService

from waivern_gdpr_data_subject_classifier import GDPRDataSubjectClassifier
from waivern_gdpr_data_subject_classifier.types import GDPRDataSubjectClassifierConfig


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


class TestGDPRDataSubjectClassifierLLMIntegration:
    """Integration tests with real LLM API for risk modifier detection."""

    @pytest.fixture
    def classifier_with_llm(self, llm_service: LLMService) -> GDPRDataSubjectClassifier:
        """Create classifier with real LLM service and validation enabled."""
        config = GDPRDataSubjectClassifierConfig.from_properties(
            {"llm_validation": {"enable_llm_validation": True}}
        )
        return GDPRDataSubjectClassifier(config=config, llm_service=llm_service)

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Output schema for classifier."""
        return Schema("gdpr_data_subject", "1.0.0")

    def _create_indicator_message(
        self,
        subject_category: str,
        evidence_content: str,
    ) -> Message:
        """Create a data_subject_indicator message for classifier input."""
        return Message(
            id="test_input",
            content={
                "findings": [
                    {
                        "subject_category": subject_category,
                        "confidence_score": 85,
                        "evidence": [{"content": evidence_content}],
                        "matched_patterns": [
                            {"pattern": subject_category, "match_count": 1}
                        ],
                        "metadata": {"source": "integration_test"},
                    }
                ]
            },
            schema=Schema("data_subject_indicator", "1.0.0"),
            run_id="integration-test-run",
        )

    @pytest.mark.integration
    def test_llm_filters_false_positive_minor_changes(
        self,
        classifier_with_llm: GDPRDataSubjectClassifier,
        output_schema: Schema,
    ) -> None:
        """LLM should NOT detect 'minor' when 'minor' means 'small changes'.

        This is a key success criterion: regex would match "minor" in
        "minor changes", but LLM understands it means "small", not "child".
        """
        # Arrange: Evidence with "minor" meaning "small changes"
        message = self._create_indicator_message(
            subject_category="patient",
            evidence_content="We made minor changes to the patient record system",
        )

        # Act
        result = classifier_with_llm.process([message], output_schema)

        # Assert: LLM should NOT flag this as involving a minor (child)
        findings = result.content["findings"]
        assert len(findings) == 1

        healthcare_finding = findings[0]
        assert "minor" not in healthcare_finding["risk_modifiers"], (
            f"LLM should understand 'minor changes' doesn't mean a child. "
            f"Got risk_modifiers: {healthcare_finding['risk_modifiers']}"
        )

    @pytest.mark.integration
    def test_llm_detects_age_based_minor(
        self,
        classifier_with_llm: GDPRDataSubjectClassifier,
        output_schema: Schema,
    ) -> None:
        """LLM should detect 'minor' from age reference like '8-year-old'.

        This is a key success criterion: regex might miss "8-year-old" but
        LLM understands this indicates a child (minor under GDPR Article 8).
        """
        # Arrange: Evidence with age indicating a minor
        message = self._create_indicator_message(
            subject_category="patient",
            evidence_content="The 8-year-old patient was admitted to the paediatric ward",
        )

        # Act
        result = classifier_with_llm.process([message], output_schema)

        # Assert: LLM should detect this involves a minor (child)
        findings = result.content["findings"]
        assert len(findings) == 1

        healthcare_finding = findings[0]
        assert "minor" in healthcare_finding["risk_modifiers"], (
            f"LLM should understand '8-year-old' indicates a minor. "
            f"Got risk_modifiers: {healthcare_finding['risk_modifiers']}"
        )

    @pytest.mark.integration
    def test_llm_detects_vulnerable_individual(
        self,
        classifier_with_llm: GDPRDataSubjectClassifier,
        output_schema: Schema,
    ) -> None:
        """LLM should detect 'vulnerable_individual' from semantic context.

        This is a key success criterion: "elderly patient with dementia"
        indicates a vulnerable individual under GDPR Recital 75, requiring
        semantic understanding that regex patterns cannot provide.
        """
        # Arrange: Evidence indicating a vulnerable individual
        message = self._create_indicator_message(
            subject_category="patient",
            evidence_content="The elderly patient with dementia requires additional care",
        )

        # Act
        result = classifier_with_llm.process([message], output_schema)

        # Assert: LLM should detect vulnerable individual
        findings = result.content["findings"]
        assert len(findings) == 1

        healthcare_finding = findings[0]
        assert "vulnerable_individual" in healthcare_finding["risk_modifiers"], (
            f"LLM should understand 'elderly with dementia' indicates vulnerability. "
            f"Got risk_modifiers: {healthcare_finding['risk_modifiers']}"
        )

    @pytest.mark.integration
    def test_metadata_includes_llm_validation_summary(
        self,
        classifier_with_llm: GDPRDataSubjectClassifier,
        output_schema: Schema,
    ) -> None:
        """Output metadata should include validation_summary with LLM details."""
        # Arrange: Any valid input
        message = self._create_indicator_message(
            subject_category="patient",
            evidence_content="Patient record for Jane Doe",
        )

        # Act
        result = classifier_with_llm.process([message], output_schema)

        # Assert: Metadata includes LLM validation info
        metadata = result.content["analysis_metadata"]
        assert metadata["llm_validation_enabled"] is True

        # Validation summary should indicate LLM was used
        assert "validation_summary" in metadata
        summary = metadata["validation_summary"]
        assert summary["method_used"] == "llm"
        assert "total_findings" in summary
        assert "llm_samples_processed" in summary
        assert "categories_validated" in summary
