"""Integration tests with real LLM APIs for ISO27001Assessor.

These tests verify that the LLM produces sensible assessment verdicts
for ISO 27001 controls — something that cannot be tested with mocks.

Run with: uv run pytest -m integration
"""

import pytest
from waivern_artifact_store.in_memory import AsyncInMemoryStore
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import LLMService
from waivern_llm.di.configuration import LLMServiceConfiguration
from waivern_llm.errors import LLMConfigurationError
from waivern_llm.providers import AnthropicProvider, GoogleProvider, OpenAIProvider
from waivern_llm.service import DefaultLLMService

from waivern_iso27001_control_assessor import ISO27001Assessor
from waivern_iso27001_control_assessor.schemas.types import (
    ControlStatus,
    EvidenceStatus,
    ISO27001AssessmentOutput,
)
from waivern_iso27001_control_assessor.types import ISO27001AssessorConfig

OUTPUT_SCHEMA = Schema("iso27001_assessment", "1.0.0")

VALID_STATUSES = {
    ControlStatus.COMPLIANT,
    ControlStatus.PARTIAL,
    ControlStatus.NON_COMPLIANT,
}


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


def _make_assessor(
    control_ref: str,
    llm_service: LLMService,
) -> ISO27001Assessor:
    """Create assessor with real LLM service."""
    config = ISO27001AssessorConfig.from_properties({"control_ref": control_ref})
    return ISO27001Assessor(config=config, llm_service=llm_service)


def _make_evidence_message(findings: list[dict[str, object]]) -> Message:
    """Build a security_evidence/1.0.0 Message from finding dicts."""
    return Message(
        id="integration_test_evidence",
        content={
            "findings": findings,
            "summary": {
                "total_findings": len(findings),
                "domains_identified": 0,
                "domains": [],
            },
            "analysis_metadata": {
                "ruleset_used": "test",
                "llm_validation_enabled": False,
            },
        },
        schema=Schema("security_evidence", "1.0.0"),
        run_id="integration-test-run",
    )


def _make_document_message(findings: list[dict[str, object]]) -> Message:
    """Build a security_document_context/1.0.0 Message from finding dicts."""
    return Message(
        id="integration_test_document",
        content={
            "findings": findings,
            "summary": {
                "total_documents": len(findings),
                "cross_cutting_count": 0,
                "domain_coverage": [],
            },
            "analysis_metadata": {
                "ruleset_used": "test",
                "llm_validation_enabled": False,
            },
        },
        schema=Schema("security_document_context", "1.0.0"),
        run_id="integration-test-run",
    )


def _parse_output(result: Message) -> ISO27001AssessmentOutput:
    """Parse a process() output Message into the typed model."""
    return ISO27001AssessmentOutput.model_validate(result.content)


class TestISO27001AssessorLLMIntegration:
    """Integration tests with real LLM API for control assessment."""

    @pytest.mark.integration
    def test_technical_control_produces_verdict_from_code_evidence(
        self, llm_service: LLMService
    ) -> None:
        """LLM should assess a cryptography control from code evidence.

        A.8.24 (use of cryptography) receives positive encryption evidence.
        The LLM should produce a valid assessment verdict with automated
        evidence_status and a meaningful rationale.
        """
        assessor = _make_assessor("A.8.24", llm_service)
        evidence_msg = _make_evidence_message(
            [
                {
                    "id": "ev-aes-256",
                    "metadata": {"source": "crypto_utils.py"},
                    "evidence_type": "CODE",
                    "security_domain": "encryption",
                    "polarity": "positive",
                    "confidence": 0.95,
                    "description": (
                        "AES-256-GCM encryption used for data at rest via "
                        "cryptography.fernet module with proper key derivation"
                    ),
                },
                {
                    "id": "ev-tls",
                    "metadata": {"source": "server_config.py"},
                    "evidence_type": "CONFIG",
                    "security_domain": "encryption",
                    "polarity": "positive",
                    "confidence": 0.90,
                    "description": (
                        "TLS 1.3 configured for all HTTPS endpoints with "
                        "strong cipher suite selection"
                    ),
                },
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        finding = output.findings[0]

        assert finding.control_ref == "A.8.24"
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert finding.status in VALID_STATUSES, (
            f"LLM should produce a definitive verdict, got: {finding.status}"
        )
        assert len(finding.rationale) > 0, "Rationale must be non-empty"
        assert output.summary.total_controls == 1
        assert output.analysis_metadata.llm_validation_enabled is True

    @pytest.mark.integration
    def test_governance_control_assessed_with_document_evidence(
        self, llm_service: LLMService
    ) -> None:
        """LLM should assess a governance control from document evidence.

        A.5.1 (policies for information security) is a document-only control
        (evidence_source=[DOCUMENT]). Providing a governance-tagged policy
        document should result in automated evidence_status and an LLM verdict.
        """
        assessor = _make_assessor("A.5.1", llm_service)
        document_msg = _make_document_message(
            [
                {
                    "id": "doc-infosec-policy",
                    "filename": "information_security_policy.md",
                    "content": (
                        "Information Security Policy\n\n"
                        "1. Purpose: This policy establishes the information "
                        "security framework for Acme Corp.\n"
                        "2. Scope: Applies to all employees, contractors, and "
                        "third-party users.\n"
                        "3. Management commitment: Senior leadership reviews "
                        "this policy annually.\n"
                        "4. Roles and responsibilities are defined in Appendix A.\n"
                        "5. Policy violations will result in disciplinary action.\n"
                        "6. This policy is approved by the CISO and CEO."
                    ),
                    "security_domains": ["governance"],
                    "metadata": {"source": "information_security_policy.md"},
                },
            ]
        )

        result = assessor.process(inputs=[document_msg], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        finding = output.findings[0]

        assert finding.control_ref == "A.5.1"
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert finding.status in VALID_STATUSES, (
            f"LLM should produce a definitive verdict, got: {finding.status}"
        )
        assert len(finding.rationale) > 0, "Rationale must be non-empty"
        assert output.analysis_metadata.llm_validation_enabled is True

    @pytest.mark.integration
    def test_mixed_control_with_both_evidence_types(
        self, llm_service: LLMService
    ) -> None:
        """LLM should assess a mixed control using both technical and document evidence.

        A.5.15 (access control) accepts both TECHNICAL and DOCUMENT evidence
        and has evidence_required=[DOCUMENT]. Providing both types satisfies the
        gate and gives the LLM the richest possible context for assessment.
        """
        assessor = _make_assessor("A.5.15", llm_service)
        evidence_msg = _make_evidence_message(
            [
                {
                    "id": "ev-rbac",
                    "metadata": {"source": "auth_middleware.py"},
                    "evidence_type": "CODE",
                    "security_domain": "access_control",
                    "polarity": "positive",
                    "confidence": 0.92,
                    "description": (
                        "Role-based access control (RBAC) implemented with "
                        "permission checks on all API endpoints using decorator "
                        "@require_role(['admin', 'editor'])"
                    ),
                },
            ]
        )
        document_msg = _make_document_message(
            [
                {
                    "id": "doc-access-policy",
                    "filename": "access_control_policy.md",
                    "content": (
                        "Access Control Policy\n\n"
                        "1. Access is granted on a need-to-know basis.\n"
                        "2. All access requests require manager approval.\n"
                        "3. Privileged access is reviewed quarterly.\n"
                        "4. Multi-factor authentication is required for admin access.\n"
                        "5. Access is revoked immediately upon termination."
                    ),
                    "security_domains": ["access_control"],
                    "metadata": {"source": "access_control_policy.md"},
                },
            ]
        )

        result = assessor.process(
            inputs=[evidence_msg, document_msg], output_schema=OUTPUT_SCHEMA
        )

        output = _parse_output(result)
        finding = output.findings[0]

        assert finding.control_ref == "A.5.15"
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert finding.status in VALID_STATUSES, (
            f"LLM should produce a definitive verdict, got: {finding.status}"
        )
        assert len(finding.rationale) > 0, "Rationale must be non-empty"
        assert output.analysis_metadata.llm_validation_enabled is True
