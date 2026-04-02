"""Tests for ISO27001Assessor.process() — standalone degraded-mode fallback.

process() delegates to prepare/finalise with LLM forced off. These tests
verify the evidence filtering and status derivation logic still works
correctly through the standalone path.
"""

from waivern_schemas.iso27001_assessment import (
    CIAProperty,
    ControlStatus,
    ControlType,
    CybersecurityConcept,
    EvidenceStatus,
    ISOSecurityDomain,
    OperationalCapability,
)

from waivern_iso27001_control_assessor import ISO27001Assessor
from waivern_iso27001_control_assessor.types import ISO27001AssessorConfig

from .test_helpers import (
    OUTPUT_SCHEMA,
    make_document_finding,
    make_document_message,
    make_evidence_finding,
    make_evidence_message,
    parse_output,
)


def _make_assessor(control_ref: str) -> ISO27001Assessor:
    """Build an assessor without LLM service (standalone mode)."""
    config = ISO27001AssessorConfig.from_properties({"control_ref": control_ref})
    return ISO27001Assessor(config=config)


# =============================================================================
# Evidence Status Derivation
# =============================================================================


class TestEvidenceStatusDerivation:
    """Tests for the evidence_status decision tree via process()."""

    def test_no_evidence_returns_insufficient_evidence(self) -> None:
        """Empty findings → insufficient_evidence, status=not_assessed."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message([])

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = parse_output(result)
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
        evidence_msg = make_evidence_message(
            [
                make_evidence_finding(security_domain="access_control"),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]

        assert finding.evidence_status == EvidenceStatus.REQUIRES_ATTESTATION
        assert finding.status == ControlStatus.NOT_ASSESSED

    def test_automated_evidence_produces_not_assessed(self) -> None:
        """Matching evidence → evidence_status=AUTOMATED but status=NOT_ASSESSED.

        process() forces LLM off, so AUTOMATED controls produce NOT_ASSESSED
        with a degraded-mode rationale.
        """
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message(
            [
                make_evidence_finding(security_domain="encryption"),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert finding.status == ControlStatus.NOT_ASSESSED

    def test_require_review_propagation_returns_requires_attestation(self) -> None:
        """Evidence with require_review=True → requires_attestation regardless."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message(
            [
                make_evidence_finding(
                    security_domain="encryption", require_review=True
                ),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = parse_output(result)
        assert output.findings[0].evidence_status == EvidenceStatus.REQUIRES_ATTESTATION
        assert output.findings[0].status == ControlStatus.NOT_ASSESSED


# =============================================================================
# Filtering Effects
# =============================================================================


class TestEvidenceFiltering:
    """Tests for domain and evidence_source filtering effects on status."""

    def test_non_matching_domain_evidence_excluded(self) -> None:
        """Evidence for a different domain is excluded → insufficient_evidence."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message(
            [
                make_evidence_finding(security_domain="access_control"),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = parse_output(result)
        assert (
            output.findings[0].evidence_status == EvidenceStatus.INSUFFICIENT_EVIDENCE
        )

    def test_document_only_control_excludes_technical_evidence(self) -> None:
        """evidence_source=[DOCUMENT] control drops all security_evidence items."""
        assessor = _make_assessor("A.5.1")
        evidence_msg = make_evidence_message(
            [
                make_evidence_finding(security_domain="governance"),
            ]
        )

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = parse_output(result)
        assert (
            output.findings[0].evidence_status == EvidenceStatus.INSUFFICIENT_EVIDENCE
        )

    def test_cross_cutting_document_produces_not_assessed(self) -> None:
        """Cross-cutting document reaches AUTOMATED but process() produces NOT_ASSESSED."""
        assessor = _make_assessor("A.8.24")
        document_msg = make_document_message(
            [
                make_document_finding(security_domains=[], filename="org-context.md"),
            ]
        )

        result = assessor.process(inputs=[document_msg], output_schema=OUTPUT_SCHEMA)

        output = parse_output(result)
        assert output.findings[0].evidence_status == EvidenceStatus.AUTOMATED
        assert output.findings[0].status == ControlStatus.NOT_ASSESSED


# =============================================================================
# Output Shape
# =============================================================================


class TestOutputShape:
    """Tests for output message structure and attribute copying."""

    def test_output_copies_iso27001_attributes_from_rule(self) -> None:
        """Five ISO 27001 attributes are copied verbatim from the matched rule."""
        assessor = _make_assessor("A.8.24")
        evidence_msg = make_evidence_message([])

        result = assessor.process(inputs=[evidence_msg], output_schema=OUTPUT_SCHEMA)

        output = parse_output(result)
        finding = output.findings[0]

        assert finding.control_type == ControlType.PREVENTIVE
        assert finding.cia == [CIAProperty.CONFIDENTIALITY, CIAProperty.INTEGRITY]
        assert finding.cybersecurity_concept == CybersecurityConcept.PROTECT
        assert (
            finding.operational_capability
            == OperationalCapability.SYSTEM_AND_NETWORK_PROTECTION
        )
        assert finding.iso_security_domain == ISOSecurityDomain.PROTECTION
