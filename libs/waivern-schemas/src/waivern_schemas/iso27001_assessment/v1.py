"""Schema data models for ISO 27001 assessment."""

import dataclasses
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseSchemaOutput,
)


class ControlStatus(StrEnum):
    """Assessment status for an individual ISO 27001 control."""

    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


class EvidenceStatus(StrEnum):
    """How the evidence for a control was obtained or why it is missing."""

    AUTOMATED = "automated"
    REQUIRES_ATTESTATION = "requires_attestation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class AssessmentVerdict:
    """Grouped verdict fields for a single control assessment."""

    status: ControlStatus
    evidence_status: EvidenceStatus
    rationale: str
    gap_description: str | None
    recommended_actions: list[str] = dataclasses.field(default_factory=list)


class ControlType(StrEnum):
    """ISO 27001 Annex A control type attribute."""

    PREVENTIVE = "preventive"
    DETECTIVE = "detective"
    CORRECTIVE = "corrective"


class CIAProperty(StrEnum):
    """CIA triad information security property."""

    CONFIDENTIALITY = "confidentiality"
    INTEGRITY = "integrity"
    AVAILABILITY = "availability"


class CybersecurityConcept(StrEnum):
    """NIST Cybersecurity Framework function alignment."""

    IDENTIFY = "identify"
    PROTECT = "protect"
    DETECT = "detect"
    RESPOND = "respond"
    RECOVER = "recover"


class ISOSecurityDomain(StrEnum):
    """ISO 27001 security domain attribute (4-value taxonomy)."""

    GOVERNANCE_AND_ECOSYSTEM = "governance_and_ecosystem"
    PROTECTION = "protection"
    DEFENCE = "defence"
    RESILIENCE = "resilience"


class OperationalCapability(StrEnum):
    """ISO 27001 Annex A operational capability tag."""

    ACCESS_CONTROL = "access_control"
    ASSET_MANAGEMENT = "asset_management"
    ASSURANCE = "assurance"
    COMPLIANCE = "compliance"
    CONTINUITY = "continuity"
    ENDPOINT_SECURITY = "endpoint_security"
    EVENT_AND_INCIDENT_MANAGEMENT = "event_and_incident_management"
    GOVERNANCE = "governance"
    HUMAN_RESOURCE_SECURITY = "human_resource_security"
    IDENTITY_AND_ACCESS_MANAGEMENT = "identity_and_access_management"
    INFORMATION_PROTECTION = "information_protection"
    PHYSICAL_SECURITY = "physical_security"
    PRIVACY = "privacy"
    SECURE_DEVELOPMENT = "secure_development"
    SUPPLIER_RELATIONSHIPS = "supplier_relationships"
    SYSTEM_AND_NETWORK_PROTECTION = "system_and_network_protection"
    THREAT_AND_VULNERABILITY_MANAGEMENT = "threat_and_vulnerability_management"


class ISO27001AssessmentMetadata(BaseFindingMetadata):
    """Metadata for ISO 27001 assessment items.

    Extends BaseFindingMetadata which provides:
    - source: str - Control reference (e.g. "A.5.1")
    - context: dict[str, object] - Extensible context for pipeline metadata
    """


class ISO27001AssessmentModel(BaseModel):
    """Individual ISO 27001 control assessment verdict.

    One instance per assessed control. Does NOT extend BaseFindingModel —
    this is an assessment verdict, not a pattern-matched finding. It has no
    evidence snippets or matched_patterns. It satisfies the Finding protocol
    (id + metadata) for LLMService.complete() compatibility.

    If future requirements arise, evidence and/or matched_patterns fields
    can be added to the model when appropriate.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this assessment (UUID)",
    )
    metadata: ISO27001AssessmentMetadata = Field(
        description="Metadata with control reference as source",
    )
    control_ref: str = Field(
        min_length=1,
        description="ISO 27001:2022 Annex A control reference (e.g. 'A.5.1')",
    )
    status: ControlStatus = Field(
        description="Assessment verdict for this control",
    )
    evidence_status: EvidenceStatus = Field(
        description="How evidence was obtained or why it is missing",
    )
    rationale: str = Field(
        description="Narrative explaining the verdict (LLM-generated or fixed message)",
    )
    gap_description: str | None = Field(
        default=None,
        description="Actionable description of gaps (None when status is compliant)",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description=(
            "Prioritised list of recommended actions to achieve or maintain compliance. "
            "Each action is specific and actionable — technical implementation, "
            "document creation/update, or evidence gathering. "
            "Empty when status is compliant."
        ),
    )
    control_type: ControlType = Field(
        description="ISO 27001 Annex A control type attribute",
    )
    cia: list[CIAProperty] = Field(
        description="CIA triad information security properties for this control",
    )
    cybersecurity_concept: CybersecurityConcept = Field(
        description="NIST CSF cybersecurity concept alignment",
    )
    operational_capability: OperationalCapability = Field(
        description="Annex A operational capability tag",
    )
    iso_security_domain: ISOSecurityDomain = Field(
        description="ISO 27001 security domain attribute (4-value taxonomy)",
    )


class ISO27001AssessmentSummary(BaseModel):
    """Summary statistics for ISO 27001 control assessments."""

    total_controls: int = Field(ge=0, description="Total number of controls assessed")
    compliant_count: int = Field(ge=0, description="Controls with status=compliant")
    partial_count: int = Field(ge=0, description="Controls with status=partial")
    non_compliant_count: int = Field(
        ge=0, description="Controls with status=non_compliant"
    )
    not_assessed_count: int = Field(
        ge=0, description="Controls with status=not_assessed"
    )
    automated_count: int = Field(
        ge=0, description="Controls with evidence_status=automated"
    )
    requires_attestation_count: int = Field(
        ge=0, description="Controls with evidence_status=requires_attestation"
    )
    insufficient_evidence_count: int = Field(
        ge=0, description="Controls with evidence_status=insufficient_evidence"
    )


class ISO27001AssessmentOutput(BaseSchemaOutput):
    """Complete output structure for iso27001_assessment schema.

    Represents the full wire format for ISO 27001 assessment results.
    One finding per control assessed, with summary statistics and
    analysis metadata.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[ISO27001AssessmentModel] = Field(
        description="List of individual control assessment verdicts",
    )
    summary: ISO27001AssessmentSummary = Field(
        description="Summary statistics across all assessed controls",
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the assessment process",
    )


__all__ = [
    "AssessmentVerdict",
    "CIAProperty",
    "ControlStatus",
    "ControlType",
    "CybersecurityConcept",
    "EvidenceStatus",
    "ISO27001AssessmentMetadata",
    "ISO27001AssessmentModel",
    "ISO27001AssessmentOutput",
    "ISO27001AssessmentSummary",
    "ISOSecurityDomain",
    "OperationalCapability",
]
