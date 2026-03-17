"""Tests for SecurityDocumentEvidenceExtractor behaviour."""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_core.testing import ProcessorContractTests
from waivern_core.types import SecurityDomain
from waivern_llm import LLMCompletionResult, LLMService

from waivern_security_document_evidence_extractor import (
    SecurityDocumentEvidenceExtractor,
)
from waivern_security_document_evidence_extractor.types import (
    DomainClassificationResponse,
    SecurityDocumentEvidenceExtractorConfig,
)

OUTPUT_SCHEMA = Schema("security_document_context", "1.0.0")


def _make_input_message(
    items: list[dict[str, Any]],
    *,
    message_id: str = "test_input",
) -> Message:
    """Build a standard_input/1.0.0 Message from content/source pairs."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="test_data",
        source="test",
        metadata={},
        data=[
            StandardInputDataItemModel(
                content=item["content"],
                metadata=BaseMetadata(
                    source=item["source"],
                    connector_type="filesystem",
                ),
            )
            for item in items
        ],
    )
    return Message(
        id=message_id,
        content=data.model_dump(exclude_none=True),
        schema=Schema("standard_input", "1.0.0"),
        run_id="test-run",
    )


def _make_extractor(
    *,
    enable_llm: bool = True,
    llm_responses: list[DomainClassificationResponse] | None = None,
) -> tuple[SecurityDocumentEvidenceExtractor, Mock | None]:
    """Create extractor with optional mocked LLM service.

    Returns:
        Tuple of (extractor, mock_llm_service_or_None).

    """
    config = SecurityDocumentEvidenceExtractorConfig(
        enable_llm_classification=enable_llm,
    )

    if not enable_llm:
        return SecurityDocumentEvidenceExtractor(config=config, llm_service=None), None

    mock_service = Mock(spec=LLMService)
    mock_service.complete = AsyncMock()
    mock_service.complete.return_value = LLMCompletionResult(
        responses=llm_responses or [],
        skipped=[],
    )

    return SecurityDocumentEvidenceExtractor(
        config=config, llm_service=mock_service
    ), mock_service


class TestSecurityDocumentEvidenceExtractorContract(
    ProcessorContractTests[SecurityDocumentEvidenceExtractor],
):
    """Contract tests for SecurityDocumentEvidenceExtractor."""

    @pytest.fixture
    def processor_class(self):
        return SecurityDocumentEvidenceExtractor


class TestSecurityDocumentEvidenceExtractor:
    """Tests for extractor processing behaviour."""

    # =========================================================================
    # Domain classification
    # =========================================================================

    def test_llm_assigned_domains_appear_in_output(self):
        """Domains returned by the LLM end up in the output model."""
        domains = [SecurityDomain.AUTHENTICATION, SecurityDomain.ACCESS_CONTROL]
        extractor, _ = _make_extractor(
            llm_responses=[
                DomainClassificationResponse(
                    security_domains=domains, summary="MFA and access control policies"
                )
            ],
        )
        msg = _make_input_message([{"content": "MFA policy doc", "source": "mfa.docx"}])

        result = extractor.process([msg], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert set(findings[0]["security_domains"]) == {
            "authentication",
            "access_control",
        }

    def test_cross_cutting_emission(self):
        """LLM returning [] produces security_domains: [] in output."""
        extractor, _ = _make_extractor(
            llm_responses=[
                DomainClassificationResponse(
                    security_domains=[], summary="ISMS overview summary"
                )
            ],
        )
        msg = _make_input_message([{"content": "ISMS overview", "source": "isms.docx"}])

        result = extractor.process([msg], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert findings[0]["security_domains"] == []

    # =========================================================================
    # Content preservation
    # =========================================================================

    def test_full_content_preserved(self):
        """Document content in output equals input file text verbatim."""
        raw_text = "Full policy text\nwith newlines\nand special chars: £€¥"
        extractor, _ = _make_extractor(
            llm_responses=[
                DomainClassificationResponse(
                    security_domains=[], summary="Policy text summary"
                )
            ],
        )
        msg = _make_input_message([{"content": raw_text, "source": "policy.txt"}])

        result = extractor.process([msg], OUTPUT_SCHEMA)

        assert result.content["findings"][0]["content"] == raw_text

    def test_filename_preserved(self):
        """Output filename matches metadata.source from input."""
        extractor, _ = _make_extractor(
            llm_responses=[
                DomainClassificationResponse(
                    security_domains=[], summary="Access control summary"
                )
            ],
        )
        msg = _make_input_message(
            [{"content": "text", "source": "access-control-policy.docx"}]
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        finding = result.content["findings"][0]
        assert finding["filename"] == "access-control-policy.docx"
        assert finding["metadata"]["source"] == "access-control-policy.docx"

    # =========================================================================
    # Multiple documents
    # =========================================================================

    def test_multiple_documents_independent_classification(self):
        """Each document gets its own independent domain classification."""
        extractor, _ = _make_extractor(
            llm_responses=[
                DomainClassificationResponse(
                    security_domains=[SecurityDomain.ENCRYPTION],
                    summary="Encryption policy summary",
                ),
                DomainClassificationResponse(
                    security_domains=[SecurityDomain.INCIDENT_MANAGEMENT],
                    summary="Incident response summary",
                ),
            ],
        )
        msg = _make_input_message(
            [
                {"content": "Encryption policy", "source": "encryption.docx"},
                {"content": "Incident response plan", "source": "incident.docx"},
            ]
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 2
        assert findings[0]["security_domains"] == ["encryption"]
        assert findings[1]["security_domains"] == ["incident_management"]

    # =========================================================================
    # LLM disabled mode
    # =========================================================================

    def test_llm_disabled_assigns_empty_domains(self):
        """With enable_llm_classification=False, all docs get [] and LLM is not called."""
        extractor, mock_service = _make_extractor(enable_llm=False)
        msg = _make_input_message(
            [
                {"content": "Doc A", "source": "a.docx"},
                {"content": "Doc B", "source": "b.docx"},
            ]
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert all(f["security_domains"] == [] for f in findings)
        assert mock_service is None

    # =========================================================================
    # Summary statistics
    # =========================================================================

    def test_summary_statistics_correct(self):
        """Output summary has correct total, cross-cutting count, and domain coverage."""
        extractor, _ = _make_extractor(
            llm_responses=[
                DomainClassificationResponse(
                    security_domains=[
                        SecurityDomain.ENCRYPTION,
                        SecurityDomain.DATA_PROTECTION,
                    ],
                    summary="Encryption and DLP summary",
                ),
                DomainClassificationResponse(
                    security_domains=[], summary="ISMS overview summary"
                ),
                DomainClassificationResponse(
                    security_domains=[SecurityDomain.ENCRYPTION],
                    summary="TLS configuration summary",
                ),
            ],
        )
        msg = _make_input_message(
            [
                {"content": "Encryption + DLP", "source": "enc.docx"},
                {"content": "ISMS overview", "source": "isms.docx"},
                {"content": "TLS config", "source": "tls.docx"},
            ]
        )

        result = extractor.process([msg], OUTPUT_SCHEMA)

        summary = result.content["summary"]
        assert summary["total_documents"] == 3
        assert summary["cross_cutting_count"] == 1
        assert sorted(summary["domain_coverage"]) == ["data_protection", "encryption"]
