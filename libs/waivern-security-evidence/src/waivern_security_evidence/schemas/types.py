"""Security evidence schema types."""

import uuid
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, Field
from waivern_core.schemas import BaseAnalysisOutputMetadata, BaseSchemaOutput


class SecurityDomain(StrEnum):
    """Framework-agnostic security domain taxonomy.

    Used as the bridge between indicator findings and compliance framework
    controls (ISO 27001 Annex A, GDPR Art 32, etc.). A single taxonomy
    shared across all producers and consumers of security_evidence.

    StrEnum serialises to plain strings in JSON — Pydantic handles this
    transparently, so no custom serialiser is needed.
    """

    AUTHENTICATION = "authentication"
    ENCRYPTION = "encryption"
    ACCESS_CONTROL = "access_control"
    LOGGING_MONITORING = "logging_monitoring"
    VULNERABILITY_MANAGEMENT = "vulnerability_management"
    DATA_PROTECTION = "data_protection"
    NETWORK_SECURITY = "network_security"
    PHYSICAL_SECURITY = "physical_security"
    PEOPLE_CONTROLS = "people_controls"
    SUPPLIER_MANAGEMENT = "supplier_management"
    INCIDENT_MANAGEMENT = "incident_management"
    BUSINESS_CONTINUITY = "business_continuity"


class SecurityEvidenceModel(BaseModel):
    """A single normalised piece of security evidence.

    Unlike indicator models (which extend BaseFindingModel and carry raw
    pattern match details), SecurityEvidenceModel is a normalised hub item.
    It abstracts over the origin of the evidence — pattern-matched code,
    config file, or LLM-extracted document section — presenting a uniform
    structure to downstream assessors.

    Fields are deliberately broad to accommodate all three evidence paths:
    - CODE/CONFIG: produced by SecurityEvidenceNormaliser (no LLM)
    - DOCUMENT:    produced by DocumentEvidenceExtractor (LLM-based)
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this evidence item (UUID)",
    )
    source_location: str = Field(
        description=(
            "Where the evidence was found. For code/config: file path. "
            "For documents: document name and section reference."
        )
    )
    evidence_type: Literal["CODE", "CONFIG", "DOCUMENT"] = Field(
        description="Origin of the evidence: CODE, CONFIG, or DOCUMENT",
    )
    security_domain: SecurityDomain = Field(
        description="Security domain this evidence relates to",
    )
    polarity: Literal["positive", "negative", "neutral"] = Field(
        description=(
            "Evidence polarity: positive (good practice), "
            "negative (bad practice / gap), or neutral (presence only)"
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for this evidence item (0.0–1.0)",
    )
    description: str = Field(
        description=(
            "Evidence content. For code/config: matched excerpt or summary. "
            "For documents: verbatim section or LLM-generated summary."
        )
    )
    require_review: bool | None = Field(
        default=None,
        description=(
            "Propagated from upstream findings. True when an upstream analyser "
            "flagged the source finding as requiring human review. "
            "Causes downstream control_assessment.evidence_status = requires_attestation."
        ),
    )


class SecurityEvidenceSummary(BaseModel):
    """Summary statistics for a security_evidence output."""

    total_findings: int = Field(
        ge=0,
        description="Total number of security evidence items",
    )


class SecurityEvidenceOutput(BaseSchemaOutput):
    """Complete output structure for security_evidence/1.0.0 schema.

    Shared hub schema produced by both SecurityEvidenceNormaliser (deterministic,
    no LLM) and DocumentEvidenceExtractor (LLM-based). Placing this in a shared
    package avoids a circular dependency between the two producer packages.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[SecurityEvidenceModel] = Field(
        description="List of normalised security evidence items",
    )
    summary: SecurityEvidenceSummary = Field(
        description="Summary statistics for this security evidence output",
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process that produced this output",
    )
