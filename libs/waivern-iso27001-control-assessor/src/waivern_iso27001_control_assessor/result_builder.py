"""Result builder for ISO 27001 control assessment output."""

import logging
from datetime import UTC, datetime

from waivern_core.message import Message
from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema
from waivern_rulesets.iso27001_domains import ISO27001DomainsRule

from .schemas.types import (
    AssessmentVerdict,
    CIAProperty,
    ControlStatus,
    ControlType,
    CybersecurityConcept,
    EvidenceStatus,
    ISO27001AssessmentMetadata,
    ISO27001AssessmentModel,
    ISO27001AssessmentOutput,
    ISO27001AssessmentSummary,
    ISOSecurityDomain,
    OperationalCapability,
)

logger = logging.getLogger(__name__)


class ISO27001ResultBuilder:
    """Builds output messages for ISO 27001 control assessments."""

    def __init__(self, domain_ruleset: str) -> None:
        """Initialise result builder.

        Args:
            domain_ruleset: Ruleset URI for analysis metadata.

        """
        self._domain_ruleset = domain_ruleset

    def build_output_message(
        self,
        rule: ISO27001DomainsRule,
        *,
        verdict: AssessmentVerdict,
        llm_enabled: bool,
        output_schema: Schema,
    ) -> Message:
        """Build a validated output message for a single control assessment.

        Constructs the finding with five ISO 27001 attributes from the rule,
        computes summary counts, serialises to JSON, and validates against
        the schema.

        Args:
            rule: The matched ISO 27001 rule (source of control attributes).
            verdict: Grouped assessment result (status, evidence_status, rationale, gap).
            llm_enabled: Whether this assessment used the LLM.
            output_schema: Schema for output validation.

        Returns:
            Validated output message.

        """
        finding = ISO27001AssessmentModel(
            metadata=ISO27001AssessmentMetadata(source=rule.control_ref),
            control_ref=rule.control_ref,
            status=verdict.status,
            evidence_status=verdict.evidence_status,
            rationale=verdict.rationale,
            gap_description=verdict.gap_description,
            control_type=ControlType(rule.control_type),
            cia=[CIAProperty(c) for c in rule.cia],
            cybersecurity_concept=CybersecurityConcept(rule.cybersecurity_concept),
            operational_capability=OperationalCapability(rule.operational_capability),
            iso_security_domain=ISOSecurityDomain(rule.iso_security_domain),
        )

        summary = ISO27001AssessmentSummary(
            total_controls=1,
            compliant_count=1 if verdict.status == ControlStatus.COMPLIANT else 0,
            partial_count=1 if verdict.status == ControlStatus.PARTIAL else 0,
            non_compliant_count=1
            if verdict.status == ControlStatus.NON_COMPLIANT
            else 0,
            not_assessed_count=1 if verdict.status == ControlStatus.NOT_ASSESSED else 0,
            automated_count=(
                1 if verdict.evidence_status == EvidenceStatus.AUTOMATED else 0
            ),
            requires_attestation_count=(
                1
                if verdict.evidence_status == EvidenceStatus.REQUIRES_ATTESTATION
                else 0
            ),
            insufficient_evidence_count=(
                1
                if verdict.evidence_status == EvidenceStatus.INSUFFICIENT_EVIDENCE
                else 0
            ),
        )

        output = ISO27001AssessmentOutput(
            findings=[finding],
            summary=summary,
            analysis_metadata=BaseAnalysisOutputMetadata(
                ruleset_used=self._domain_ruleset,
                llm_validation_enabled=llm_enabled,
            ),
        )

        result_data = output.model_dump(mode="json", exclude_none=True)
        output_message = Message(
            id=f"iso27001_assessment_{rule.control_ref}_{datetime.now(UTC).isoformat()}",
            content=result_data,
            schema=output_schema,
        )
        output_message.validate()

        logger.info(
            "ISO27001Assessor [%s]: evidence_status=%s, status=%s",
            rule.control_ref,
            verdict.evidence_status.value,
            verdict.status.value,
        )

        return output_message
