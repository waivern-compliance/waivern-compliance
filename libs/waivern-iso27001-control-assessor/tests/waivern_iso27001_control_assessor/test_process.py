"""Tests for ISO27001Assessor.process() — evidence filtering and status derivation."""

from unittest.mock import Mock

from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import LLMService

from waivern_iso27001_control_assessor import ISO27001Assessor
from waivern_iso27001_control_assessor.schemas.types import (
    CIAProperty,
    ControlStatus,
    ControlType,
    CybersecurityConcept,
    EvidenceStatus,
    ISO27001AssessmentOutput,
    ISOSecurityDomain,
    OperationalCapability,
)
from waivern_iso27001_control_assessor.types import ISO27001AssessorConfig

OUTPUT_SCHEMA = Schema("iso27001_assessment", "1.0.0")


def _make_assessor(control_ref: str) -> ISO27001Assessor:
    """Build an assessor instance for a given control."""
    config = ISO27001AssessorConfig.from_properties({"control_ref": control_ref})
    return ISO27001Assessor(config=config, llm_service=Mock(spec=LLMService))


def _make_evidence_message(
    findings: list[dict[str, object]],
) -> Message:
    """Build a security_evidence/1.0.0 Message from finding dicts."""
    return Message(
        id="test_evidence",
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
    )


def _make_document_message(
    findings: list[dict[str, object]],
) -> Message:
    """Build a security_document_context/1.0.0 Message from finding dicts."""
    return Message(
        id="test_document",
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
    )


def _make_evidence_finding(
    security_domain: str = "encryption",
    evidence_type: str = "CODE",
    require_review: bool | None = None,
) -> dict[str, object]:
    """Build a minimal SecurityEvidenceModel dict."""
    return {
        "id": "ev-1",
        "metadata": {"source": "test.py"},
        "evidence_type": evidence_type,
        "security_domain": security_domain,
        "polarity": "positive",
        "confidence": 0.9,
        "description": "Test evidence",
        "require_review": require_review,
    }


def _make_document_finding(
    security_domains: list[str] | None = None,
    filename: str = "policy.md",
) -> dict[str, object]:
    """Build a minimal SecurityDocumentContextModel dict."""
    return {
        "id": "doc-1",
        "filename": filename,
        "content": "Test document content",
        "security_domains": security_domains or [],
        "metadata": {"source": filename},
    }


def _parse_output(result: Message) -> ISO27001AssessmentOutput:
    """Parse a process() output Message into the typed model."""
    return ISO27001AssessmentOutput.model_validate(result.content)


# =============================================================================
# Evidence Status Derivation
# =============================================================================


class TestEvidenceStatusDerivation:
    """Tests for the evidence_status decision tree."""

    def test_no_evidence_returns_insufficient_evidence(self) -> None:
        """No inputs at all → insufficient_evidence, status=not_assessed."""
        assessor = _make_assessor("A.8.24")
        result = assessor.process(inputs=[], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        finding = output.findings[0]

        assert finding.evidence_status == EvidenceStatus.INSUFFICIENT_EVIDENCE
        assert finding.status == ControlStatus.NOT_ASSESSED
        assert finding.control_ref == "A.8.24"

    def test_evidence_required_missing_returns_requires_attestation(self) -> None:
        """evidence_required=[DOCUMENT] with only technical evidence → requires_attestation.

        A.5.15 has evidence_source=[TECHNICAL, DOCUMENT], evidence_required=[DOCUMENT].
        Providing only technical evidence fails the evidence_required gate.
        """
        assessor = _make_assessor("A.5.15")
        evidence_msg = _make_evidence_message(
            [
                _make_evidence_finding(security_domain="access_control"),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        finding = output.findings[0]

        assert finding.evidence_status == EvidenceStatus.REQUIRES_ATTESTATION
        assert finding.status == ControlStatus.NOT_ASSESSED

    def test_evidence_required_satisfied_returns_automated(self) -> None:
        """evidence_required=[DOCUMENT] with both technical and document evidence → automated.

        A.5.15 has evidence_required=[DOCUMENT]. Providing both types satisfies the gate.
        """
        assessor = _make_assessor("A.5.15")
        evidence_msg = _make_evidence_message(
            [
                _make_evidence_finding(security_domain="access_control"),
            ]
        )
        document_msg = _make_document_message(
            [
                _make_document_finding(security_domains=["access_control"]),
            ]
        )

        result = assessor.process(
            inputs=[evidence_msg, document_msg], output_schema=OUTPUT_SCHEMA
        )

        output = _parse_output(result)
        assert output.findings[0].evidence_status == EvidenceStatus.AUTOMATED

    def test_require_review_propagation_returns_requires_attestation(self) -> None:
        """Evidence with require_review=True → requires_attestation regardless.

        Even when evidence matches the domain, the require_review flag forces
        requires_attestation to ensure human review.
        """
        assessor = _make_assessor("A.8.24")
        evidence_msg = _make_evidence_message(
            [
                _make_evidence_finding(
                    security_domain="encryption", require_review=True
                ),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        assert output.findings[0].evidence_status == EvidenceStatus.REQUIRES_ATTESTATION
        assert output.findings[0].status == ControlStatus.NOT_ASSESSED

    def test_matching_evidence_returns_automated(self) -> None:
        """Matching evidence for the control's domain → automated.

        A.8.24 (cryptography) has security_domains=[encryption].
        Providing encryption-domain evidence should result in automated.
        """
        assessor = _make_assessor("A.8.24")
        evidence_msg = _make_evidence_message(
            [
                _make_evidence_finding(security_domain="encryption"),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        assert output.findings[0].evidence_status == EvidenceStatus.AUTOMATED


# =============================================================================
# Filtering Effects
# =============================================================================


class TestEvidenceFiltering:
    """Tests for domain and evidence_source filtering effects on status."""

    def test_non_matching_domain_evidence_excluded(self) -> None:
        """Evidence for a different domain is excluded → insufficient_evidence.

        A.8.24 has security_domains=[encryption]. Providing access_control
        evidence should be filtered out, leaving no evidence.
        """
        assessor = _make_assessor("A.8.24")
        evidence_msg = _make_evidence_message(
            [
                _make_evidence_finding(security_domain="access_control"),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        assert (
            output.findings[0].evidence_status == EvidenceStatus.INSUFFICIENT_EVIDENCE
        )

    def test_document_only_control_excludes_technical_evidence(self) -> None:
        """evidence_source=[DOCUMENT] control drops all security_evidence items.

        A.5.1 has evidence_source=[DOCUMENT]. Technical security_evidence
        items should be dropped, leaving no evidence.
        """
        assessor = _make_assessor("A.5.1")
        evidence_msg = _make_evidence_message(
            [
                _make_evidence_finding(security_domain="governance"),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        assert (
            output.findings[0].evidence_status == EvidenceStatus.INSUFFICIENT_EVIDENCE
        )

    def test_cross_cutting_document_reaches_any_control(self) -> None:
        """Document with security_domains=[] passes through to any control.

        A.8.24 is a technical control (encryption), but a cross-cutting
        document (e.g. org-context.md) should still reach it as background.
        """
        assessor = _make_assessor("A.8.24")
        document_msg = _make_document_message(
            [
                _make_document_finding(security_domains=[], filename="org-context.md"),
            ]
        )

        result = assessor.process(inputs=[document_msg], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        assert output.findings[0].evidence_status == EvidenceStatus.AUTOMATED


# =============================================================================
# Output Shape
# =============================================================================


class TestOutputShape:
    """Tests for output message structure and attribute copying."""

    def test_output_copies_iso27001_attributes_from_rule(self) -> None:
        """Five ISO 27001 attributes are copied verbatim from the matched rule.

        A.8.24 (use of cryptography) has known attribute values in the ruleset.
        These must appear in the output regardless of evidence_status.
        """
        assessor = _make_assessor("A.8.24")
        result = assessor.process(inputs=[], output_schema=OUTPUT_SCHEMA)

        output = _parse_output(result)
        finding = output.findings[0]

        assert finding.control_type == ControlType.PREVENTIVE
        assert finding.cia == [CIAProperty.CONFIDENTIALITY, CIAProperty.INTEGRITY]
        assert finding.cybersecurity_concept == CybersecurityConcept.PROTECT
        assert (
            finding.operational_capability
            == OperationalCapability.SYSTEM_AND_NETWORK_PROTECTION
        )
        assert finding.iso_security_domain == ISOSecurityDomain.PROTECTION
