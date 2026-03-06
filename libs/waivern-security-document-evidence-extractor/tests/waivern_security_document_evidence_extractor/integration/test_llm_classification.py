"""Integration tests with real LLM APIs for SecurityDocumentEvidenceExtractor.

These tests verify that the LLM correctly classifies policy documents
by security domain — something that cannot be tested with mocks.

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
from waivern_core.types import SecurityDomain
from waivern_llm import LLMService
from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.errors import LLMConfigurationError
from waivern_llm.providers import AnthropicProvider, GoogleProvider, OpenAIProvider
from waivern_llm.service import DefaultLLMService

from waivern_security_document_evidence_extractor import (
    SecurityDocumentEvidenceExtractor,
)
from waivern_security_document_evidence_extractor.types import (
    SecurityDocumentEvidenceExtractorConfig,
)

OUTPUT_SCHEMA = Schema("security_document_context", "1.0.0")


@pytest.fixture
def llm_service() -> LLMService:
    """Create LLM service based on .env configuration.

    Skips the test if LLM service is not configured.
    """
    try:
        config = LLMServiceConfiguration.from_properties({})
    except Exception as e:
        pytest.skip(f"LLM service not configured: {e}")

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

    return DefaultLLMService(provider=provider, store=cache_store)


def _make_extractor(llm_service: LLMService) -> SecurityDocumentEvidenceExtractor:
    """Create extractor with real LLM service."""
    config = SecurityDocumentEvidenceExtractorConfig(enable_llm_classification=True)
    return SecurityDocumentEvidenceExtractor(config=config, llm_service=llm_service)


def _make_input_message(content: str, source: str) -> Message:
    """Build a single-document standard_input/1.0.0 Message."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="integration_test",
        source="integration_test",
        metadata={},
        data=[
            StandardInputDataItemModel(
                content=content,
                metadata=BaseMetadata(source=source, connector_type="filesystem"),
            )
        ],
    )
    return Message(
        id="integration_test",
        content=data.model_dump(exclude_none=True),
        schema=Schema("standard_input", "1.0.0"),
        run_id="integration-test-run",
    )


class TestSecurityDocumentEvidenceExtractorLLMIntegration:
    """Integration tests with real LLM API for domain classification."""

    @pytest.mark.integration
    def test_encryption_policy_classified_correctly(
        self, llm_service: LLMService
    ) -> None:
        """LLM should classify an encryption policy under the encryption domain.

        This verifies the prompt produces sensible domain assignments for
        a clearly domain-specific document.
        """
        extractor = _make_extractor(llm_service)
        msg = _make_input_message(
            content=(
                "Encryption Policy\n\n"
                "1. All data at rest must be encrypted using AES-256.\n"
                "2. All data in transit must use TLS 1.2 or higher.\n"
                "3. Encryption keys must be rotated annually.\n"
                "4. Key management procedures must follow NIST SP 800-57.\n"
                "5. Full disk encryption is required on all endpoints."
            ),
            source="encryption-policy.docx",
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 1

        domains = findings[0]["security_domains"]
        assert SecurityDomain.ENCRYPTION.value in domains, (
            f"LLM should classify encryption policy under 'encryption' domain. "
            f"Got: {domains}"
        )

    @pytest.mark.integration
    def test_cross_cutting_document_gets_empty_domains(
        self, llm_service: LLMService
    ) -> None:
        """LLM should return [] for an organisational context document.

        Cross-cutting documents that apply equally to all domains should
        receive an empty security_domains list.
        """
        extractor = _make_extractor(llm_service)
        msg = _make_input_message(
            content=(
                "Organisation Context\n\n"
                "Acme Corp is a mid-size SaaS company with 150 employees.\n"
                "We operate in the financial technology sector.\n"
                "Our tech stack includes Python, PostgreSQL, and AWS.\n"
                "The information security team consists of 3 full-time staff.\n"
                "We are pursuing ISO 27001 certification."
            ),
            source="org-context.docx",
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["security_domains"] == [], (
            f"LLM should classify org context as cross-cutting (empty domains). "
            f"Got: {findings[0]['security_domains']}"
        )

    @pytest.mark.integration
    def test_output_structure_valid(self, llm_service: LLMService) -> None:
        """Output message has correct structure with findings, summary, and metadata."""
        extractor = _make_extractor(llm_service)
        msg = _make_input_message(
            content="Access control policy: implement RBAC for all systems.",
            source="access-control.docx",
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content

        summary = result.content["summary"]
        assert summary["total_documents"] == 1
        assert isinstance(summary["domain_coverage"], list)

        metadata = result.content["analysis_metadata"]
        assert metadata["llm_validation_enabled"] is True
